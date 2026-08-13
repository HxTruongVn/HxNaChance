"""Repository Intake Workshop UI.

The UI is a thin client over core.review. It exposes the full dossier workflow:
source → quarantine → inspection → profile completion → integration plan →
resource registration → scaffold → contract test → approval.
"""
from __future__ import annotations

import json
from pathlib import Path

from core.review.inspector import report_to_dict
from core.review.models import IntegrationMode
from core.review.workflow import ReviewWorkflow



def _theme_text_color(colors, role="text_primary"):
    """Use the host NaChance theme for workshop UI text."""
    return colors.get(role) if isinstance(colors, dict) else None

class RepoIntakeUIMixin:
    def _build_repo_intake_tab(self):
        import customtkinter as ctk
        from tkinter import filedialog, messagebox

        self._repo_intake_workflow = ReviewWorkflow(
            Path(__file__).resolve().parents[2] / ".nachance" / "quarantine",
            warehouse_root=Path(__file__).resolve().parents[2] / ".nachance" / "warehouse",
            scaffold_root=Path(__file__).resolve().parents[2] / "workshops",
        )
        self._repo_intake_case = None
        self._repo_intake_vars = {}
        self._repo_intake_messagebox = messagebox
        self._repo_intake_filedialog = filedialog

        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        ctk.CTkLabel(frame, text="Repository Intake", font=self.F_HEADER,
                     text_color=self.COLORS["text_primary"]).pack(anchor="w", padx=16, pady=(16, 2))
        ctk.CTkLabel(frame,
                     text="Tiếp nhận repo lạ trong quarantine, cấp/hoàn thiện hồ sơ, đăng ký Resource và tạo adapter scaffold trước khi phê duyệt.",
                     wraplength=760, justify="left", text_color=self.COLORS["text_secondary"]).pack(anchor="w", padx=16, pady=(0, 12))

        source = ctk.CTkFrame(frame, fg_color=self.COLORS["bg_card"], corner_radius=8)
        source.pack(fill="x", padx=16, pady=(0, 10))
        self._repo_intake_source = ctk.StringVar(value="")
        ctk.CTkEntry(source, textvariable=self._repo_intake_source, placeholder_text="Thư mục / ZIP / đường dẫn repo").pack(side="left", fill="x", expand=True, padx=(10, 6), pady=10)
        ctk.CTkButton(source, text="Thư mục", width=80, command=self._repo_intake_choose_folder).pack(side="left", padx=3, pady=10)
        ctk.CTkButton(source, text="ZIP", width=55, command=self._repo_intake_choose_zip).pack(side="left", padx=3, pady=10)
        ctk.CTkButton(source, text="Tiếp nhận", width=90, fg_color=self.COLORS["accent"], hover_color=self.COLORS["accent_hover"], command=self._repo_intake_submit).pack(side="left", padx=(3, 10), pady=10)

        self._repo_intake_state = ctk.CTkLabel(frame, text="Chưa có hồ sơ", font=self.F_MEDIUM, text_color=self.COLORS["text_secondary"])
        self._repo_intake_state.pack(anchor="w", padx=16, pady=(0, 8))

        self._repo_intake_section(frame, "Hồ sơ Workshop — có thể cấp/bổ sung khi repo thiếu")
        profile_grid = ctk.CTkFrame(frame, fg_color=self.COLORS["bg_card"], corner_radius=8)
        profile_grid.pack(fill="x", padx=16, pady=(0, 10))
        fields = [
            ("workshop_id", "ID"), ("name", "Tên"), ("version", "Version"),
            ("description", "Mô tả"), ("author", "Tác giả"), ("license", "License"),
            ("source_url", "Source URL"), ("source_revision", "Commit / Tag"),
            ("entrypoint", "Entrypoint"), ("runtime", "Runtime (JSON)"),
            ("capabilities_required", "Capabilities bắt buộc (CSV)"), ("capabilities_optional", "Capabilities tùy chọn (CSV)"),
            ("io", "Input / Output (JSON)"), ("network", "Network"), ("offline", "Offline"),
            ("timeout_seconds", "Timeout (giây)"), ("cancel_supported", "Cancel"), ("notes", "Ghi chú"),
        ]
        for row, (key, label) in enumerate(fields):
            ctk.CTkLabel(profile_grid, text=label, text_color=self.COLORS["text_secondary"], anchor="w").grid(row=row, column=0, sticky="ew", padx=(12, 8), pady=5)
            var = ctk.StringVar(value="")
            self._repo_intake_vars[key] = var
            entry = ctk.CTkEntry(profile_grid, textvariable=var)
            entry.grid(row=row, column=1, sticky="ew", padx=(0, 12), pady=5)
            if key in {"description", "notes", "io", "runtime"}: entry.configure(height=32)
        profile_grid.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(profile_grid, text="Cấp / lưu hồ sơ", command=self._repo_intake_save_profile).grid(row=len(fields), column=1, sticky="e", padx=12, pady=(8, 12))

        self._repo_intake_section(frame, "Inspection / Intake Report")
        self._repo_intake_report_box = ctk.CTkTextbox(frame, height=260, wrap="word")
        self._repo_intake_report_box.pack(fill="x", padx=16, pady=(0, 10))
        self._repo_intake_report_box.insert("1.0", "Chưa có intake report.")
        self._repo_intake_report_box.configure(state="disabled")

        actions = ctk.CTkFrame(frame, fg_color=self.COLORS["bg_card"], corner_radius=8)
        actions.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkLabel(actions, text="Integration plan", text_color=self.COLORS["text_primary"]).grid(row=0, column=0, padx=12, pady=10, sticky="w")
        self._repo_intake_plan = ctk.CTkComboBox(actions, values=[m.value for m in IntegrationMode], width=190)
        self._repo_intake_plan.set(IntegrationMode.PROCESS.value)
        self._repo_intake_plan.grid(row=0, column=1, padx=4, pady=10)
        buttons = [
            ("Lưu phương án", self._repo_intake_select_plan),
            ("Register Resources", self._repo_intake_register_resources),
            ("Build Scaffold", self._repo_intake_build_scaffold),
            ("Contract Test", self._repo_intake_contract_test),
            ("Approve", self._repo_intake_approve),
        ]
        for col, (label, command) in enumerate(buttons, 2):
            ctk.CTkButton(actions, text=label, command=command, width=125).grid(row=0, column=col, padx=3, pady=10)
        actions.grid_columnconfigure(7, weight=1)
        return frame

    def _menu_repo_intake_content(self, menu=None):
        """Optional menu hook; lifecycle remains owned by Core WindowManager."""
        if menu is not None:
            menu.add_command(label="Repository Intake", command=self._open_repo_intake)

    def _open_repo_intake(self):
        """Focus the already-managed Repo Intake window; never create a second one."""
        focus = getattr(self, "focus_workshop", None)
        if callable(focus):
            focus()
        return self

    def _repo_intake_section(self, parent, title):
        import customtkinter as ctk
        ctk.CTkLabel(parent, text=title, font=self.F_MEDIUM, text_color=self.COLORS["accent"]).pack(anchor="w", padx=16, pady=(8, 6))

    def _repo_intake_choose_folder(self):
        selected = self._repo_intake_filedialog.askdirectory(title="Chọn repository cần tiếp nhận")
        if selected: self._repo_intake_source.set(selected)

    def _repo_intake_choose_zip(self):
        selected = self._repo_intake_filedialog.askopenfilename(title="Chọn repository ZIP", filetypes=[("ZIP", "*.zip"), ("All files", "*.*")])
        if selected: self._repo_intake_source.set(selected)

    def _repo_intake_submit(self):
        source = self._repo_intake_source.get().strip()
        if not source:
            self._repo_intake_messagebox.showwarning("Thiếu repo", "Hãy chọn thư mục hoặc ZIP trước."); return
        try:
            case = self._repo_intake_workflow.submit(source, source_label=source)
        except Exception as exc:
            self._repo_intake_messagebox.showerror("Không thể tiếp nhận repo", str(exc)); return
        self._repo_intake_case = case
        self._repo_intake_load_profile(case.profile)
        self._repo_intake_refresh(case)

    def _repo_intake_load_profile(self, profile):
        if profile is None: return
        for key, var in self._repo_intake_vars.items():
            value = getattr(profile, key, "")
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            var.set("" if value is None else str(value))

    def _repo_intake_profile_values(self):
        values = {key: var.get().strip() for key, var in self._repo_intake_vars.items()}
        for key in ("runtime", "io"):
            if values[key]:
                values[key] = json.loads(values[key])
        for key in ("capabilities_required", "capabilities_optional"):
            values[key] = [x.strip() for x in values[key].split(",") if x.strip()]
        if values["timeout_seconds"]:
            values["timeout_seconds"] = int(values["timeout_seconds"])
        else:
            values["timeout_seconds"] = None
        return values

    def _repo_intake_save_profile(self):
        if self._repo_intake_case is None:
            self._repo_intake_messagebox.showwarning("Chưa có repo", "Hãy tiếp nhận repo trước."); return
        try:
            profile = self._repo_intake_workflow.complete_profile(self._repo_intake_case, self._repo_intake_profile_values())
        except Exception as exc:
            self._repo_intake_messagebox.showerror("Hồ sơ chưa hợp lệ", str(exc)); return
        self._repo_intake_load_profile(profile); self._repo_intake_refresh(self._repo_intake_case)
        if profile.missing_fields:
            self._repo_intake_messagebox.showwarning("Hồ sơ còn thiếu", "Cần bổ sung: " + ", ".join(profile.missing_fields))

    def _repo_intake_select_plan(self):
        case = self._repo_intake_case
        if case is None:
            self._repo_intake_messagebox.showwarning("Chưa có hồ sơ", "Hãy tiếp nhận repo trước."); return
        try: self._repo_intake_workflow.select_plan(case, IntegrationMode(self._repo_intake_plan.get()))
        except Exception as exc: self._repo_intake_messagebox.showerror("Không thể chọn phương án", str(exc)); return
        self._repo_intake_refresh(case)

    def _repo_intake_register_resources(self):
        try: self._repo_intake_workflow.register_resources(self._repo_intake_case); self._repo_intake_refresh(self._repo_intake_case)
        except Exception as exc: self._repo_intake_messagebox.showerror("Resource intake thất bại", str(exc))

    def _repo_intake_build_scaffold(self):
        try: self._repo_intake_workflow.build_scaffold(self._repo_intake_case); self._repo_intake_refresh(self._repo_intake_case)
        except Exception as exc: self._repo_intake_messagebox.showerror("Không tạo được scaffold", str(exc))

    def _repo_intake_contract_test(self):
        try: self._repo_intake_workflow.contract_test(self._repo_intake_case); self._repo_intake_refresh(self._repo_intake_case)
        except Exception as exc: self._repo_intake_messagebox.showerror("Contract test thất bại", str(exc))

    def _repo_intake_approve(self):
        if self._repo_intake_case is None: return
        approver = self._repo_intake_messagebox.askquestion("Phê duyệt", "Phê duyệt hồ sơ này sau khi contract test đã đạt?")
        if approver != "yes": return
        try:
            self._repo_intake_workflow.approve(self._repo_intake_case, approver="desktop-user")
            self._repo_intake_refresh(self._repo_intake_case)
        except Exception as exc: self._repo_intake_messagebox.showerror("Không thể phê duyệt", str(exc))

    def _repo_intake_refresh(self, case):
        self._repo_intake_state.configure(text=f"{case.state.value.upper()}  •  {case.case_id}")
        payload = {"case_id": case.case_id, "state": case.state.value, "quarantine_path": case.quarantine_path,
                   "integration_mode": case.integration_mode.value if case.integration_mode else None,
                   "contract_results": case.contract_results, "events": case.events}
        if case.report: payload["intake_report"] = report_to_dict(case.report)
        if case.profile: payload["profile"] = case.profile.to_dict()
        if case.resource_registry_path: payload["resource_registry"] = case.resource_registry_path
        if case.adapter_path: payload["adapter_path"] = case.adapter_path
        self._repo_intake_report_box.configure(state="normal")
        self._repo_intake_report_box.delete("1.0", "end")
        self._repo_intake_report_box.insert("1.0", json.dumps(payload, ensure_ascii=False, indent=2))
        self._repo_intake_report_box.configure(state="disabled")
