**NaChance Architecture Vision**

**Version: 1.0**



**Mục đích**

Tài liệu này không mô tả cách lập trình.

Tài liệu này mô tả tư tưởng thiết kế của NaChance nhằm giúp mọi lập trình viên, AI và cộng tác viên đưa ra các quyết định kiến trúc nhất quán trong suốt quá trình phát triển dự án.

Nếu có sự khác biệt giữa giải pháp ngắn hạn và định hướng dài hạn, ưu tiên giữ đúng định hướng.



**NaChance là gì?**

NaChance là một nền tảng xử lý ảnh được thiết kế để có thể mở rộng lâu dài.

Mục tiêu của NaChance không phải là tích hợp thật nhiều AI.

Mục tiêu của NaChance là xây dựng một kiến trúc cho phép:

bổ sung AI mới;

thay thế AI cũ;

mở rộng chức năng;

thay đổi công nghệ;

mà không phải thiết kế lại toàn bộ hệ thống.



Vấn đề mà NaChance muốn giải quyết

Trong hầu hết các phần mềm AI hiện nay:

chương trình thường phụ thuộc vào một model cụ thể;

pipeline thường được viết cố định;

việc thay đổi AI kéo theo thay đổi mã nguồn.

Điều này làm cho hệ thống khó mở rộng khi công nghệ thay đổi.

NaChance hướng tới việc giảm sự phụ thuộc này.



**Triết lý thiết kế**

Kiến trúc của NaChance ưu tiên:

mô tả chức năng hơn là mô tả công nghệ;

tách biệt trách nhiệm giữa các thành phần;

khả năng thay thế độc lập;

khả năng mở rộng lâu dài.

Một quyết định thiết kế tốt là quyết định giúp hệ thống thích nghi với công nghệ mới mà không phải thay đổi kiến trúc cốt lõi.



Người dùng chỉ quan tâm mục tiêu

Người dùng không cần biết:

AI nào được sử dụng;

weight nào đang chạy;

framework nào đang được cài;

pipeline bên trong được tổ chức như thế nào.

Người dùng chỉ cần mô tả mục tiêu.

Ví dụ:

Khôi phục ảnh cũ.

Làm rõ khuôn mặt.

Đổi nền.

Tô màu.

Chuẩn bị ảnh hộ chiếu.

Việc lựa chọn cách thực hiện là trách nhiệm của hệ thống.



AI chỉ là thành phần

Trong NaChance:

AI Model không phải trung tâm của kiến trúc.

AI chỉ là một thành phần có khả năng thực hiện một hoặc nhiều chức năng.

Không AI nào được phép trở thành thành phần bắt buộc của toàn bộ hệ thống.

Nếu trong tương lai xuất hiện AI tốt hơn, việc thay thế phải diễn ra với ảnh hưởng nhỏ nhất tới phần còn lại của dự án.



Không phụ thuộc vào Pipeline

Pipeline hiện tại có thể phù hợp với công nghệ hiện tại.

Nhưng kiến trúc không được giả định rằng pipeline đó sẽ tồn tại mãi mãi.

Trong tương lai:

có thể thay đổi trình tự xử lý;

có thể thay đổi AI;

có thể thêm hoặc bỏ một bước xử lý.

Kiến trúc phải cho phép điều này mà không cần viết lại toàn bộ hệ thống.



**Metadata quan trọng hơn Hard-code**

Khi có thể lựa chọn, ưu tiên mô tả hệ thống bằng dữ liệu (metadata, cấu hình, khai báo) thay vì ghi cứng trong mã nguồn.

Điều này giúp:

mở rộng dễ hơn;

giảm phụ thuộc;

giảm số lượng vị trí phải sửa khi có thay đổi.

Không phải mọi thứ đều cần metadata, nhưng metadata nên được ưu tiên đối với những thành phần có khả năng mở rộng.



**Thiết kế theo khả năng thay thế**

Mỗi thành phần nên có khả năng được thay thế độc lập.

Ví dụ:

AI Model;

Weight;

Package;

Python Environment;

CUDA;

Plugin.

Việc thay thế một thành phần không nên kéo theo việc sửa nhiều khu vực không liên quan.



**Tách biệt trách nhiệm**

Mỗi thành phần chỉ nên chịu một nhóm trách nhiệm chính.

Ví dụ:

UI chịu trách nhiệm tương tác với người dùng.

Runtime chịu trách nhiệm chuẩn bị và quản lý môi trường thực thi.

Module AI chịu trách nhiệm xử lý AI.

Setup chịu trách nhiệm cài đặt.

Registry (nếu có) chịu trách nhiệm quản lý thông tin thành phần.

Không nên để một module vừa xử lý giao diện, vừa điều phối AI, vừa cài đặt môi trường.



**Hiện trạng của dự án**

Tại thời điểm viết tài liệu này, NaChance vẫn đang trong quá trình xây dựng nền móng.

Ưu tiên hiện tại là:

Runtime ổn định;

Bootstrap độc lập;

Setup tự động;

Quản lý Weight;

Cấu trúc thư mục rõ ràng;

Tách biệt các thành phần.

Một số ý tưởng trong tài liệu này vẫn chưa được triển khai và chỉ đóng vai trò định hướng.



**Định hướng phát triển**

Trong tương lai, NaChance có thể từng bước bổ sung:

Registry quản lý thành phần.

Metadata cho AI và tài nguyên.

Cơ chế đăng ký Provider.

Khả năng lựa chọn phương án thực thi phù hợp.

Plugin mở rộng.

Các hướng phát triển này sẽ chỉ được triển khai khi phù hợp với quy mô của dự án.

Không coi đây là yêu cầu bắt buộc của phiên bản hiện tại.



**Nguyên tắc khi bổ sung tính năng mới**

Trước khi thêm một tính năng mới, hãy tự hỏi:

Thành phần mới có làm tăng sự phụ thuộc không?

Có thể thay thế nó trong tương lai không?

Có đang hard-code một công nghệ cụ thể không?

Có làm kiến trúc khó mở rộng hơn không?

Có thể tách trách nhiệm rõ ràng hơn không?

Nếu một quyết định làm hệ thống phụ thuộc mạnh hơn vào một công nghệ hiện tại, hãy cân nhắc lại.



**Tầm nhìn dài hạn**

NaChance không hướng tới việc chỉ hỗ trợ một AI.

NaChance cũng không hướng tới việc chỉ phục vụ một quy trình xử lý ảnh.

NaChance hướng tới một kiến trúc có khả năng thích nghi với sự thay đổi của công nghệ trong nhiều năm tiếp theo.

**Những gì thay đổi sẽ là:**

AI;

Weight;

Framework;

Pipeline;

Công cụ.

**Những gì cần được giữ ổn định là:**

kiến trúc;

trách nhiệm của từng thành phần;

nguyên tắc mở rộng;

khả năng thay thế.



**Kim chỉ nam**

Thiết kế cho sự thay đổi, không thiết kế cho công nghệ hiện tại.

Kiến trúc phải tồn tại lâu hơn bất kỳ AI Model nào.

