# Add this to your urls.py file
from django.urls import path
from .views import home
from myapp import views
# In your project's urls.py
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('login/', views.login_view, name='login'),
    path('payroll/', views.payroll_view, name='payroll'),
    path('payroll/<int:payslip_id>/', views.payroll_view, name='payroll_detail'),
    path('payroll/download/<int:payslip_id>/', views.download_payslip, name='download_payslip'),
    path('salary/', views.salary_view, name='salary'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('leave/', views.leave_view, name='leave'),
    path('settings/', views.settings_view, name='settings'),
    path('request-leave/', views.request_leave_view, name='request_leave'),
    path("request-leave/success/", views.request_leave_success, name="request_leave_success"),
    path('manager/leaves/', views.manager_leaves_view, name='manager_leaves_view'),
    path('manager/leave/<int:leave_id>/<str:action>/', views.leave_action_view, name='leave_action'),
    path("leave-summary/", views.leave_summary_view, name="leave_summary"),
    path("get-leave-report/", views.get_leave_report, name="get_leave_report"),
    path('submit_salary', views.submit_salary, name='submit_salary'),
    path('settings/update_profile/', views.update_profile, name='update_profile'),
    path('settings/update_profile_pass/', views.update_profile_pass, name='update_profile_pass'),
    path('employee/', views.employee_view, name='employee'),
    path('employee/manage/', views.employee_manage_view, name='employee_manage'),
    path('employee/update-role/<int:employee_id>/', views.update_employee_role, name='update_employee_role'),
    path('employee/details/<int:employee_id>/', views.get_employee_details, name='get_employee_details'),
    
    path('employee/update-employee/', views.update_employee, name='update_employee'),
    
    path('cancel-leave/<int:leave_id>/', views.cancel_leave_view, name='cancel_leave'),


    # Add this line for the profile image update
    path('update-profile-image/', views.update_profile_image, name='update_profile_image'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)