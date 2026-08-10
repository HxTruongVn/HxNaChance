"""ui.pipeline_mixin — PipelineMixin: chạy xử lý ảnh (đơn + batch) qua
worker thread. NHÓM RỦI RO CAO NHẤT khi tách (README có ghi nhận bug
thread-safety cũ ở
đúng nhóm method này: "Config thu thập từ UI TRƯỚC khi chạy worker
thread"). Test kỹ cả xử lý đơn lẻ lẫn batch sau khi merge.
"""
import os
import tempfile
import threading
from datetime import datetime
from tkinter import filedialog, messagebox

import cv2

from ui.utils import imwrite_unicode as _imwrite_unicode, open_folder as _open_folder


class PipelineMixin:
    def _run_single(self):
        # FIX: nâng cấp từ askopenfilename (1 file) lên askopenfilenames
        # (chọn nhiều file cùng lúc) — vẫn giữ đúng hành vi cũ khi chỉ
        # chọn 1 file, nhưng giờ chọn nhiều file cũng chạy được qua cùng
        # 1 nút, không bắt buộc phải "Xử lý thư mục" nếu chỉ muốn xử lý
        # vài ảnh cụ thể (không phải cả thư mục).
        file_paths = filedialog.askopenfilenames(
            title="Chọn ảnh (chọn được nhiều file)",
            filetypes=[("Ảnh", "*.jpg *.jpeg *.png *.bmp *.tiff"), ("Tất cả", "*.*")])
        if not file_paths:
            return
        file_paths = list(file_paths)

        if self.chk_confirm_orientation.get():
            def _on_confirmed(confirmed_paths):
                if confirmed_paths:
                    self._process_files(confirmed_paths)
            self._start_orientation_queue(file_paths, _on_confirmed)
        else:
            self._process_files(file_paths)

    def _run_batch(self):
        folder = filedialog.askdirectory(title="Chọn thư mục chứa ảnh")
        if not folder:
            return
        exts = (".jpg", ".jpeg", ".png", ".bmp", ".tiff")
        files = sorted([os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(exts)])
        if not files:
            messagebox.showwarning("Thông báo", "Không tìm thấy ảnh!")
            return

        if self.chk_confirm_orientation.get():
            def _on_confirmed(confirmed_paths):
                if confirmed_paths:
                    self._process_files(confirmed_paths)
            self._start_orientation_queue(files, _on_confirmed)
        else:
            self._process_files(files)

    def _process_files(self, files):
        if self.engine is None:
            messagebox.showerror("Lỗi", "Engine chưa khởi tạo. Khởi động lại app hoặc kiểm tra console.")
            return

        self._set_busy(True)
        self.status.configure(text=f"Đang xử lý 0/{len(files)}...", text_color=self.COLORS['warning'])
        self.update()

        # FIX: Thu thập toàn bộ config từ UI trước khi chạy thread
        try:
            spec = self._get_spec()
            bg_color = self._get_bg_color()
            options = self._get_options()
            quality = int(getattr(self, 'sld_chất_lượng', None).get() if hasattr(self, 'sld_chất_lượng') else 95)
        except Exception as e:
            messagebox.showerror("Lỗi cấu hình", str(e))
            self._set_busy(False)
            return

        def process(spec, bg_color, options, quality):
            results = []
            self.last_results = []
            self.current_document = None  # reset — Document của lô mới, ảnh cuối cùng xử lý thành công sẽ được giữ lại
            try:
                for i, path in enumerate(files):
                    try:
                        self.after(0, lambda idx=i+1, total=len(files):
                            self.status.configure(text=f"Đang xử lý {idx}/{total}..."))

                        agent_result = self.qa_agent.process(path, spec, bg_color, options)
                        result = agent_result.engine_result
                        # Thêm 2 field mới, không đụng field cũ — code phía
                        # dưới (result['success']/['image']/...) không đổi.
                        result['agent_verdict'] = agent_result.verdict
                        result['agent_attempts'] = len(agent_result.attempts)

                        if result['success'] and result['image'] is not None:
                            now = datetime.now()
                            folder = os.path.join(self.save_dir, str(now.year), f"thang {now.month:02d}")
                            os.makedirs(folder, exist_ok=True)

                            base_name = os.path.splitext(os.path.basename(path))[0]
                            filename = f"{now.day:02d}-{now.hour}h{now.minute}m{now.second}s-{base_name}.jpg"
                            save_path = os.path.join(folder, filename)

                            if _imwrite_unicode(save_path, result['image'], [cv2.IMWRITE_JPEG_QUALITY, quality]):
                                result['save_path'] = save_path
                                self.last_results.append(result['image'])
                                # Chỉ giữ Document của ảnh xử lý gần nhất trong
                                # RAM (đã xác nhận phạm vi — không giữ cả lô).
                                # File đã lưu ra đĩa ở trên không bị ảnh hưởng
                                # dù Document của ảnh trước đó bị thay thế.
                                self.current_document = agent_result.document
                            else:
                                result['validation_errors'].append(f"Không lưu được ảnh: {save_path}")

                        results.append((path, result))
                    except Exception as e:
                        results.append((path, {'success': False, 'validation_errors': [str(e)]}))
            except Exception as e:
                results.append(("", {'success': False, 'validation_errors': [f"Lỗi hệ thống: {e}"]}))
            finally:
                self.after(0, lambda: self._on_process_done(results))

        threading.Thread(target=process, args=(spec, bg_color, options, quality), daemon=True).start()

    def _on_process_done(self, results):
        success = sum(1 for _, r in results if r.get('success'))
        failed = len(results) - success
        needs_reshoot = sum(1 for _, r in results if r.get('agent_verdict') == 'needs_reshoot')

        if failed == 0 and needs_reshoot == 0:
            self.status.configure(text=f"✓ Hoàn thành: {success} ảnh", text_color=self.COLORS['success'])
            self.btn_run.configure(text="✅ HOÀN THÀNH", fg_color=self.COLORS['success'])
        elif needs_reshoot > 0:
            self.status.configure(
                text=f"✓ {success} | ⚠ {needs_reshoot} ảnh cần chụp lại",
                text_color=self.COLORS['warning'])
        else:
            self.status.configure(text=f"✓ {success} | ✗ {failed}", text_color=self.COLORS['warning'])

        # Thu thập chi tiết lỗi & đường dẫn đã lưu
        error_details = []
        saved_paths = []
        for path, r in results:
            if not r.get('success'):
                errs = r.get('validation_errors', [])
                err_msg = "; ".join(errs) if errs else "Lỗi không xác định"
                fname = os.path.basename(path) if path else "?"
                error_details.append(f"• {fname}: {err_msg}")
            elif r.get('save_path'):
                saved_paths.append(r['save_path'])

        if error_details:
            msg = "Một số ảnh xử lý thất bại:\n\n" + "\n".join(error_details[:5])
            if len(error_details) > 5:
                msg += f"\n...và {len(error_details)-5} ảnh khác."
            messagebox.showerror("Lỗi xử lý", msg)

        if saved_paths:
            folder = os.path.dirname(saved_paths[-1])
            msg = f"Đã lưu {len(saved_paths)} ảnh vào:\n{folder}"
            if messagebox.askyesno("Hoàn thành", msg + "\n\nBạn có muốn mở thư mục không?"):
                _open_folder(folder)

        # FIX: last_result trước đây chỉ được gán khi tick "Preview", khiến
        # Luôn cập nhật last_result khi có
        # ảnh xử lý thành công; nút xem trước vẫn ẩn/hiện riêng theo
        # checkbox preview.
        if self.last_results:
            self.last_result = self.last_results[-1]
            if self.chk_preview.get():
                self.btn_preview.pack(pady=5, padx=10, fill="x")

        # FIX: Hủy timer cũ trước khi đặt timer mới
        if self._process_timer_id is not None:
            self.after_cancel(self._process_timer_id)
        self._process_timer_id = self.after(3000, self._reset_ui)

    def _undo(self):
        """Lùi 1 bước trên Document đang active (ảnh xử lý gần nhất) —
        Giai đoạn 11. Không undo được nếu chưa xử lý ảnh nào, hoặc đã ở
        bước đầu tiên (ảnh gốc)."""
        if self.current_document is None or not self.current_document.can_undo():
            self.status.configure(text="Không còn bước nào để Undo", text_color=self.COLORS['text_secondary'])
            return
        self.current_document.undo()
        self.last_result = self.current_document.current_image
        self._show_preview()
        self.status.configure(
            text=f"↶ Undo — đang ở bước {self.current_document.cursor + 1}/{len(self.current_document.steps)}",
            text_color=self.COLORS['warning'])

    def _redo(self):
        if self.current_document is None or not self.current_document.can_redo():
            self.status.configure(text="Không còn bước nào để Redo", text_color=self.COLORS['text_secondary'])
            return
        self.current_document.redo()
        self.last_result = self.current_document.current_image
        self._show_preview()
        self.status.configure(
            text=f"↷ Redo — đang ở bước {self.current_document.cursor + 1}/{len(self.current_document.steps)}",
            text_color=self.COLORS['warning'])

