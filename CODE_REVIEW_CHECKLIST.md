# 🔍 Code Review & Naming Checklist

Dùng checklist này khi review PR hoặc trước khi commit code.

---

## 📋 Pre-Commit Checklist

### Naming & Convention
- [ ] **Files**: Tất cả `.py` files là `snake_case` (ví dụ: `photo_engine_v2.py` ✓)
- [ ] **Classes**: PascalCase với suffix rõ (Processor, Manager, Engine, Analyzer...)
- [ ] **Functions/Methods**: snake_case, bắt đầu bằng verb (parse_, enhance_, detect_...)
- [ ] **Private methods**: Có `_` prefix (ví dụ: `def _to_tensor()`)
- [ ] **Boolean methods**: Bắt đầu `is_`, `has_`, `can_`, `should_`
- [ ] **Variables**: snake_case, mô tả rõ (không `m`, `x`, `data` mơ hồ)
- [ ] **Image variables**: Có suffix type (`.bgr`, `.rgb`, `_map`)
- [ ] **Constants**: UPPER_CASE_WITH_UNDERSCORES ở top file
- [ ] **Imports**: Organized (std lib → third-party → local)

### Type Hints & Documentation
- [ ] **Function signatures**: Có type hints (`def func(x: int) -> str:`)
- [ ] **Public classes**: Có docstring
- [ ] **Public methods**: Có docstring (Google style)
- [ ] **Complex logic**: Có comments giải thích
- [ ] **No redundant comments**: Tránh `# increment i` trên `i += 1`

### Code Quality
- [ ] **No dead code**: Xóa code cũ, commented-out code
- [ ] **No magic numbers**: Dùng constants hoặc có comments
- [ ] **DRY principle**: Không copy-paste logic (tối đa 2 lần)
- [ ] **Error handling**: Try-except với messages rõ ràng
- [ ] **No print() debugging**: Dùng logging nếu cần debug output

### Performance & Resources
- [ ] **Lazy imports**: Module nặng (torch, cv2...) import trong function khi cần
- [ ] **No circular imports**: Check import graph
- [ ] **Memory leaks**: Releases resources (GPU, sessions) trong `__del__` hoặc cleanup methods
- [ ] **No unnecessary copies**: NumPy arrays, PIL Images

### Testing & Validation
- [ ] **Edge cases handled**: Empty inputs, None values, wrong types
- [ ] **Error messages**: Helpful & actionable (không `Error`)
- [ ] **Backward compatibility**: Không break existing code nếu không cần
- [ ] **File operations**: Handle file not found, permission errors

---

## 🎯 PR Template for Review

Khi tạo PR, sử dụng template này:

```markdown
## 📝 Description
[Mô tả ngắn gọn thay đổi]

## 🎯 Type
- [ ] Bug fix
- [ ] Feature
- [ ] Refactor
- [ ] Documentation
- [ ] Convention/Style

## ✅ Checklist
- [ ] Naming conventions followed (CONVENTIONS.md)
- [ ] Type hints added
- [ ] Docstrings added (public API)
- [ ] No dead code
- [ ] No print/console logging
- [ ] Tested locally
- [ ] No breaking changes

## 🔗 Related Issues
[Closes #123, Related to #456]

## 📸 Screenshots/Output
[If applicable]
```

---

## 🏆 Naming Anti-Patterns to Avoid

| ❌ Bad | ✅ Good | Reason |
|-------|--------|--------|
| `process_image_with_enhancement()` | `enhance_face()` | Quá dài, action rõ ràng |
| `img`, `I`, `im` | `image_bgr` | Rõ ràng, có type suffix |
| `data`, `result`, `value` | `parsing_map`, `face_data` | Mô tả cụ thể |
| `m`, `mask` | `skin_mask`, `eye_mask` | Rõ type mask |
| `p`, `parse` | `parse_face()` | Descriptive verb |
| `Core.py`, `PhotoEngine.py` | `photo_engine_v2.py` | Consistent casing, version |
| `Helper`, `Util`, `Tool` | `FaceParsingProcessor` | Descriptive suffix |
| `do_enhance()`, `perform_parse()` | `enhance()`, `parse()` | Động từ đơn giản |
| `PhotoX`, `PhotoY`, `PhotoZ` | `FaceAnalyzer`, `BackgroundProcessor` | Suffix rõ ràng |
| `NUM_CLASSES` (variable) | `num_classes` (variable), `NUM_CLASSES` (constant) | Type phù hợp |

---

## 🔧 Quick Fixes

### Rename theo convention

Khi setup linter/IDE, auto-format:

```python
# Before
def Process(img, fidelity=0.7):
    result_img = enhance_face_img(img)
    return result_img

# After
def enhance(image_bgr: np.ndarray, fidelity: float = 0.7) -> np.ndarray:
    enhanced_image = _enhance_face(image_bgr)
    return enhanced_image
```

---

## 📚 Reference Commands

Tìm kiếm violations (grep tips):

```bash
# Tìm hàm không theo snake_case
grep -r "def [A-Z]" --include="*.py"

# Tìm variable không rõ ràng
grep -r "= [a-z]$" --include="*.py"

# Tìm print debugging
grep -r "print(" --include="*.py"

# Tìm TODO/FIXME chưa làm
grep -r "TODO\|FIXME" --include="*.py"
```

---

## 🎓 Learning Resources

- **PEP 8** (Python Style Guide): https://pep8.org
- **Google Python Style Guide**: https://google.github.io/styleguide/pyguide.html
- **Real Python - Naming Conventions**: Real Python tutorials

---

## 💾 Checklist Tích Lũy

### Commit message format
```
[Type] Brief description

Optional longer description.

- Bullet point 1
- Bullet point 2

Fixes #123
```

**Types**:
- `[fix]` - Bug fix
- `[feat]` - Feature
- `[refactor]` - Code refactor
- `[docs]` - Documentation
- `[style]` - Convention/naming fix
- `[test]` - Test addition/fix
- `[perf]` - Performance improvement

### Example
```
[feat] Add MediaPipe face parsing support

Replace BiSeNet with MediaPipe for MIT-compatible licensing.
Maintains same API surface for backward compatibility.

- Initialize MediaPipe Face Mesh on first use
- Extract skin/eye/teeth masks from face landmarks
- Update photo_engine_v2.py to use new parser
- Update README with license changes

Fixes #42
```

---

**Last Updated**: 2026-07-26  
**Version**: 1.0  
**Author**: Photo Master Pro Team
