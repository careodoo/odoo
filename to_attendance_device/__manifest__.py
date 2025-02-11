{
    'name': "Biometric Attendance Machines Integration",
    'name_vi_VN': "Tích hợp Máy chấm công Sinh trắc học",

    'summary': """
Integrate all kinds of ZKTeco based attendance machines with Odoo""",
    'summary_vi_VN': """
Tích hợp tất cả các loại máy chấm công nền tảng ZKTeco với Odoo""",

    'description': """
Key Features
============

* Compatible on Odoo.sh as well as on Premise
* Support both UDP and TCP for large attendance data (tested with a real machine that store more than 90 thousand attendance records).
* Support connection with either domain name or IP.
* Authenticate machines with password.
* Multiple machines for multiple locations.
* Multiple machine time zones at multiple locations.
* Multiple Attendance Status support (e.g. Check-in, Check-out, Start Overtime, End Overtime, etc).
* Store fingerprint templates in employee profiles to quickly set up new a machine (Added since version 1.1.0).
* Delete Machine's Users from Odoo.
* Upload new users into the machines from Odoo's Employee database.
* Auto Map Machine Users with Odoo employee base on Badge ID mapping, or name search mapping if no Badge ID match is found.
* Store Machine Attendance data permanently.
* Manual/Automatic download attendance data from all your machines into Odoo (using scheduled actions).
* Manual/Automatic synchronize machine attendance data with HR Attendance so that you can access them in your salary rules for payslip computation.
* Automatically Clear Attendance Data from the machines periodically, which is configurable.
* Designed to work with all attendance machines that based on ZKTeco platform.

  * Fully TESTED with the following machines:

    * RONALD JACK B3-C
    * ZKTeco K50
    * ZKTeco MA300
    * ZKTeco U580
    * ZKTeco T4C
    * ZKTeco G3
    * RONALD JACK iClock260
    * ZKTeco K14
    * iFace702
    * ZKTeco H5L
    * Uface 800 (worked with finger and face)

  * Reported by clients that the module has worked great with the following machines

    * ZKTeco K40
    * ZKTeco K20
    * ZKTeco U580
    * ZKTeco F18
    * ZKTeco F19
    * iFace402/ID
    * iFace800
    * iClock3000
    * iClock880-H
    * iclock 700​
    * Ronald Jack T8
    * Ronald jack 1000Plus
    * ZKTeco MB20
    * ZKteco IN0A-1
    * ZKTeco H5L
    * Uface 800
    * SpeedFace V5L
    * VF680
    * RSP10k1
    * ... (please advise us your machines. Tks!)

INTRODUCE ADSM ICLOUD FEATURE
=============================
Since Odoo 17, new feature was added call 'Icloud' to allow machine to push data into software. Before we only can get data from the machine, some client might get trouble when configure the machine because it need static IP and Modem configuration.
With this feature (optional, by default we still use either UDP or TCP one, we encourage to use this icloud option as the last one only because it has some security risk) you only need to configure in the machine by following instruction (this instruction use SpeedFace-H5L[P], but don't worry other machines have the same one):

* Go to 'Comm' setting of the machine
* Select Cloud Server Setting and you will see some configuration:

  * Enable Domain Nam: enable this if you going to use domain name
  * Server Address: enter ip address like 192.168.1.1 (check this by going to internet setting) or your domain name like example.viindoo.com
  * Server Port: If it hosted online, probably '443' is fine or any port that your server has. In the local environment it should be the port to run odoo config (8069 for example)
  * Enable Proxy Server (Some machines have): activate Proxy, after that you will need to specify Server IP and Port of the proxy one
  * HTTPS (Some machines have): Support https when pusing data, need to activate this unless you use local environment to develop. Note this, some machines might not have this, in that case it is necessary to change the nginx settings to prevent redirection to https for routers related to machines.
  * Then go to machine manager to create a new one with protocol 'icloud' , we have choose the best setting for you so you do not need to do that
  * Fill the 'Serial Number' (In the machine, go to 'System Info' -> 'Device Info' to see the Serial Number)
  * Hit button 'Upload Setting' to push setting into the machine
  * From now on, your machine is ready to push data into the software

Credit
======
Tons of thanks to Fananimi for his pyzk library @ https://github.com/fananimi/pyzk

We got inspired from that and customize it for more features (machine information, Python 3 support,
TCP/IP support, etc) then we integrated into Odoo by this great Attendance Machine application

Known Issue
===========

* To make this module work perfectly, your device will need to be available on internet (in case you use online platform like odoo.sh or self-hosted)
* Don't worry if the device is connected but still cannot download data, it could be one of following reason:

  * Wrong device mode (we support mode call 'Time Attendance' other mode like 'Access Control' will not work)
  * Lacking device configuration (by default some device will ignore the in/out checking stuff therefore we can not download your attendance data)

Whatever the case is, you can always contact us at https://viindoo.com/ticket/team/8 for troubleshooting.

Editions Supported
==================
1. Community Edition
2. Enterprise Edition

    """,
      'description_vi_VN': """
Tính năng
=========

* Tương thích trên nền tảng Odoo.sh và cả với On Premise
* Hỗ trợ cả UDP và TCP cho lượng dữ liệu điểm danh lớn (được thử nghiệm với lưu trữ hơn 90 nghìn dữ liệu điểm danh cho một máy chấm công).
* Hỗ trợ kết nối bằng IP hoặc tên miền thiết bị.
* Xác thực kết nối thiết bị bằng mật khẩu.
* Nhiều thiết bị cho nhiều địa điểm điểm danh.
* Có thể sử dụng thiết bị với nhiều múi giờ tại nhiều địa điểm.
* Hỗ trợ nhiều trạng thái điểm danh (ví dụ: Check-in, Check-out, Bắt đầu thêm giờ, Kết thúc thêm giờ, v.v.).
* Xóa dữ liệu chấm công từ Odoo.
* Nhập dữ liệu người dùng mới từ dữ liệu nhân viên trong Odoo.
* Có thể khớp dữ liệu người dùng với hồ sơ nhân viên trong Odoo bằng cách ánh xạ ID điểm danh hoặc tìm kiếm theo tên nếu không thấy kết quả của ID phù hợp.
* Lưu dữ liệu trên máy chấm công vĩnh viễn.
* Dữ liệu điểm danh có thể tải tự động hoặc thủ công từ tất cả các máy vào Odoo (sử dụng hành động định kỳ).
* Đồng bộ hóa dữ liệu điểm danh trên thiết bị và module điểm danh trên phần mềm tự động hoặc thủ công để có thể lấy dữ liệu đưa vào tính toán tại các quy tắc lương trên phiếu lương của nhân viên.
* Tự động xóa dữ liệu trên thiết bị theo định kỳ được cài đặt trước.
* Được thiết kế để hoạt động với tất cả các thiết bị chấm công với nền tảng ZKTeco.

  * Đã được KIỂM THỬ đầy đủ với các thiết bị sau:

    * RONALD JACK B3-C
    * ZKTeco K50
    * ZKTeco MA300
    * ZKTeco U580
    * ZKTeco T4C
    * RONALD JACK iClock260
    * ZKTeco K14
    * iFace702
    * Uface 800 (hoạt động tốt với cả vân tay và khuôn mặt)

  * Được ghi nhận bởi người dùng rằng module hoạt động tốt trên các thiết bị sau:

    * ZKTeco K40
    * ZKTeco K20
    * ZKTeco U580
    * ZKTeco F18
    * ZKTeco F19
    * iFace402/ID
    * iFace800
    * iClock3000
    * iClock880-H
    * iclock 700​
    * Ronald Jack T8
    * Ronald jack 1000Plus
    * ZKTeco MB20
    * ZKteco IN0A-1
    * Uface 800
    * SpeedFace V5L
    * VF680
    * RSP10k1
    * ... (vui lòng cung cấp thiết bị của bạn. Xin cảm ơn)

GIỚI THIỆU TÍNH NĂNG ADSM ICLOUD
================================
Kể từ Odoo 17, tính năng mới được thêm vào gọi là 'Icloud' để cho phép máy chấm cổng đẩy dữ liệu vào phần mềm. Trước đây chúng ta chỉ có thể lấy dữ liệu từ máy, một số khách hàng có thể gặp rắc rối khi cấu hình máy vì nó cần cấu hình IP tĩnh và Modem mạng.
Với tính năng này (tính năng tùy chọn, mặc định chúng tôi vẫn sử dụng giao thức UDP hoặc TCP, chúng tôi khuyến khích sử dụng tùy chọn icloud này làm phương án cuối cùng vì nó có một số rủi ro về bảo mật) bạn chỉ cần cấu hình trong máy theo hướng dẫn (hướng dẫn này hãy sử dụng SpeedFace-H5L[P], nhưng đừng lo các máy khác cũng có cơ chế tương tự):

* Vào cài đặt 'Comm' của máy
* Chọn Cloud Server Setting và bạn sẽ thấy một số cấu hình:

  * Enable Domain Name: kích hoạt tính năng này nếu bạn định sử dụng tên miền
  * Server Address: nhập địa chỉ IP như 192.168.1.1 (kiểm tra điều này bằng cách vào cài đặt internet) hoặc tên miền của bạn như example.viindoo.com
  * Server Port: Nếu nó được lưu trữ trực tuyến, có thể '443' hoặc bất kỳ cổng nào mà máy chủ của bạn có. Trong môi trường nội bộ, nó phải là cổng để chạy cấu hình odoo (ví dụ 8069)
  * Enable Proxy Server (Một số máy có): kích hoạt Proxy, sau đó bạn cần chỉ định IP Server và Port của proxy
  * HTTPS (Một số máy có): Hỗ trợ https khi đẩy dữ liệu, cần kích hoạt tính năng này trừ khi bạn sử dụng môi trường nội bộ để phát triển. Lưu ý điều này, một số máy có thể không có điều này, trong trường hợp đó cần phải thay đổi cài đặt nginx để ngăn chặn việc điều hướng sang https đối với các router liên quan đến máy chấm công.

  * Sau đó vào menu quán lý máy chấm công để tạo một cái mới với giao thức 'icloud', chúng tôi đã chọn cài đặt tốt nhất cho bạn nên bạn không cần phải làm gì cả
  * Điền "Sô sê ri" (Trong máy chấm công vào "System Info" -> "Device Info" để xem Số Sê ri)
  * Nhấn nút 'Upload Setting' để đẩy cài đặt vào máy chấm công
  * Từ nay máy của bạn đã sẵn sàng để đẩy dữ liệu vào phần mềm

Thông tin thêm
==============
Xin gửi lời cảm ơn chân thành đến Fananimi vì thư viện pyzk của anh ấy @ https://github.com/fananimi/pyzk

Chúng tôi đã lấy ý tưởng từ đó và tùy chỉnh để có nhiều tính năng hơn (thông tin thiết bị, hỗ trợ Python 3,
Hỗ trợ TCP / IP, v.v.) sau đó chúng tôi tích hợp vào Odoo bằng ứng dụng máy chấm công tuyệt vời này

Vấn đề đã biết
==============

* Để mô-đun này hoạt động hoàn hảo, thiết bị của bạn cần phải có kết nối internet (trong trường hợp bạn sử dụng nền tảng trực tuyến như odoo.sh hoặc tự thuể máy chủ)
* Đừng lo lắng nếu thiết bị đã kết nối nhưng vẫn không tải được dữ liệu, có thể là một trong những nguyên nhân sau:

  * Chế độ thiết bị sai (chúng tôi hỗ trợ gọi chế độ 'Time Attendance', chế độ khác như 'Access Control' sẽ không hoạt động)
  * Thiếu cấu hình thiết bị (mặc định một số thiết bị sẽ bỏ qua việc kiểm tra vào/ra nên chúng tôi không thể tải xuống dữ liệu vào/ra của bạn)

Dù thế nào đi nữa, bạn luôn có thể liên hệ với chúng tôi qua https://viindoo.com/vi/ticket/team/8 để giải quyết vấn đề.

Ấn bản được hỗ trợ
==================
1. Ấn bản Community
2. Ấn bản Enterprise

    """,

    'author': "T.V.T Marine Automation (aka TVTMA),Viindoo",
    'live_test_url': "https://v16demo-int.viindoo.com",
    'live_test_url_vi_VN': "https://v16demo-vn.viindoo.com",
    'demo_video_url': "https://youtu.be/KP82jfDWCQU",
    'website': 'https://viindoo.com/apps/app/16.0/to_attendance_device',
    'support': 'apps.support@viindoo.com',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '1.1.5',

    # any module necessary for this one to work correctly
    'depends': ['hr_attendance', 'to_base'],

    'external_dependencies': {
        'python': ['setuptools'],
    },

    # always loaded
    'data': [
        'data/scheduler_data.xml',
        'data/attendance_state_data.xml',
        'data/mail_template_data.xml',
        'data/attendance_device_trans_flag_data.xml',
        'security/module_security.xml',
        'security/ir.model.access.csv',
        'views/menu_view.xml',
        'views/attendance_device_views.xml',
        'views/attendance_state_views.xml',
        'views/attendance_device_location.xml',
        'views/device_user_views.xml',
        'views/hr_attendance_views.xml',
        'views/hr_employee_views.xml',
        'views/user_attendance_views.xml',
        'views/attendance_activity_views.xml',
        'views/attendance_command_to_device_view.xml',
        'views/attendance_datalog_from_device_view.xml',
        'views/finger_template_views.xml',
        'wizard/employee_upload_wizard.xml',
        'wizard/device_confirm_wizard.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'price': 198.9,
    'currency': 'EUR',
    'license': 'OPL-1',
}
