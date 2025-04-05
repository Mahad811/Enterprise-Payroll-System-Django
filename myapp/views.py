from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.db.models import Sum, Count, Q, F, ExpressionWrapper, fields, IntegerField
from django.http import JsonResponse
from django.db.models.functions import ExtractDay
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Q
from .models import Employee, Leave, Salary
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from django.core.files.base import ContentFile
from django.contrib.auth import login, logout
from django.db import connection
from datetime import datetime
from django.contrib.auth.decorators import login_required
import io
import os
import base64




def home(request):
    return render(request, "login.html")  # Renders the login page


# ---------------- Signup View ----------------
def signup_view(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        username = request.POST.get("username")  # Unused in model, remove if unnecessary
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        department = request.POST.get("department")

        # Check if passwords match
        if password != confirm_password:
            return render(request, "signup.html", {"error_message": "Passwords do not match"})

        # Check if email already exists
        if Employee.objects.filter(email=email).exists():
            return render(request, "signup.html", {"error_message": "Email already registered"})

        # Create a new employee
        employee = Employee(
            first_name=first_name,
            last_name=last_name,
            email=email,
            department=department
        )
        employee.set_password(password)  # Securely hash the password before saving
        employee.save()

        # Redirect to login after signup
        return redirect("login")

    return render(request, "signup.html")

# ---------------- Login View ----------------
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        
        try:
            employee = Employee.objects.get(email=email)
            if employee.check_password(password):  # Securely check password
                request.session["user_id"] = employee.id  # Store user session
                return redirect("dashboard")
            else:
                return render(request, "login.html", {"error_message": "Invalid credentials"})

        except Employee.DoesNotExist:
            return render(request, "login.html", {"error_message": "User does not exist"})

    return render(request, "login.html")

# ---------------- Logout View ----------------
def logout_view(request):
    request.session.flush()  # Clear session
    return redirect("login")

# ---------------- Dashboard View ----------------
def dashboard_view(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    
    employee = Employee.objects.get(id=user_id)
    
    # Fetch recent leave request activities
    leave_activities = []
    
    # Get employee's own leave requests
    user_leaves = Leave.objects.filter(employee=employee).order_by('-requested_on')[:5]
    for leave in user_leaves:
        activity = {
            'title': f"{leave.leave_type} Leave Request {leave.status}",
            'date': leave.requested_on,
            'description': f"Your {leave.leave_type} leave request from {leave.start_date} to {leave.end_date} has been {leave.status.lower()}."
        }
        leave_activities.append(activity)
    
    # If employee is a manager, fetch leave requests they need to approve
    if employee.role == "Manager":
        pending_leaves = Leave.objects.filter(status="Pending").exclude(employee=employee).order_by('-requested_on')[:5]
        for leave in pending_leaves:
            activity = {
                'title': f"New Leave Request",
                'date': leave.requested_on,
                'description': f"{leave.employee.first_name} {leave.employee.last_name} requested {leave.leave_type} leave from {leave.start_date} to {leave.end_date}."
            }
            leave_activities.append(activity)
    
    # Sort activities by date (newest first)
    leave_activities.sort(key=lambda x: x['date'], reverse=True)
    
    return render(request, "index.html", {
        "employee": employee,
        "announcements": leave_activities[:5]  # Limit to 5 most recent announcements
    })

# ---------------- Payroll View ----------------
def payroll_view(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    
    try:
        employee = Employee.objects.get(id=user_id)
        
        # Fetch all salary records for the current employee
        payslips = Salary.objects.filter(employee_id=user_id).order_by('-generated_on')
        
        # Add month and year attributes to each payslip for display
        for payslip in payslips:
            payslip.month = payslip.generated_on.strftime('%B')  # Full month name
            payslip.year = payslip.generated_on.year
            payslip.status = "Processed"  # Default status
            payslip.net_salary = payslip.net_pay+800  # Match the template's expected attribute
        
        # Get the selected payslip if ID is provided
        selected_payslip_id = request.GET.get('id')
        selected_payslip = None
        
        if selected_payslip_id:
            try:
                selected_payslip = Salary.objects.get(id=selected_payslip_id, employee_id=user_id)
                selected_payslip.month = selected_payslip.generated_on.strftime('%B')
                selected_payslip.year = selected_payslip.generated_on.year
                selected_payslip.status = "Processed"
                selected_payslip.net_salary = selected_payslip.net_pay+800
                
                # Add common deductions and allowances for display
                selected_payslip.housing_allowance = Decimal('500.00')
                selected_payslip.transport_allowance = Decimal('300.00')
                selected_payslip.allowances = selected_payslip.housing_allowance + selected_payslip.transport_allowance
                selected_payslip.deductions = selected_payslip.tax
                selected_payslip.month = selected_payslip.generated_on.strftime('%B')
                selected_payslip.year = selected_payslip.generated_on.year
                selected_payslip.total_earnings = selected_payslip.basic_salary + 800
                
            except Salary.DoesNotExist:
                pass
        
        return render(request, 'payroll.html', {
            'user': {
                'get_full_name': f"{employee.first_name} {employee.last_name}",
                'employee': employee,
            
            },
            'payslips': payslips,
            'selected_payslip': selected_payslip,
        })
        
    except Employee.DoesNotExist:
        return redirect("login")


def download_payslip(request, payslip_id):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    
    try:
        employee = Employee.objects.get(id=user_id)
        payslip = Salary.objects.get(id=payslip_id, employee_id=user_id)
        
        # Create a file-like buffer to receive PDF data
        buffer = io.BytesIO()
        
        # Create the PDF object, using the buffer as its "file"
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Add company header
        p.setFont("Helvetica-Bold", 16)
        p.drawString(1 * inch, 10 * inch, "False 9 2 5")
        p.setFont("Helvetica", 12)
        p.drawString(1 * inch, 9.7 * inch, "Siraiki Adda")
        p.drawString(1 * inch, 9.4 * inch, "Email: hr@false925.com")
        
        # Add title
        p.setFont("Helvetica-Bold", 14)
        month_name = payslip.generated_on.strftime('%B')
        year = payslip.generated_on.year
        p.drawString(1 * inch, 8.7 * inch, f"Salary Slip - {month_name} {year}")
        
        # Add employee information
        p.setFont("Helvetica-Bold", 12)
        p.drawString(1 * inch, 8.0 * inch, "Employee Information")
        p.setFont("Helvetica", 12)
        p.drawString(1 * inch, 7.7 * inch, f"Name: {employee.first_name} {employee.last_name}")
        p.drawString(1 * inch, 7.4 * inch, f"Employee ID: {employee.id}")
        p.drawString(1 * inch, 7.1 * inch, f"Pay Period: {month_name} {year}")
        
        # Add earnings section
        p.setFont("Helvetica-Bold", 12)
        p.drawString(1 * inch, 6.4 * inch, "Earnings")
        p.line(1 * inch, 6.3 * inch, 7 * inch, 6.3 * inch)
        p.setFont("Helvetica", 12)
        p.drawString(1 * inch, 6.0 * inch, "Basic Salary")
        p.drawString(6 * inch, 6.0 * inch, f"${payslip.basic_salary}")
        
        p.setFont("Helvetica-Bold", 12)
        p.drawString(1 * inch, 5.6 * inch, "Total Earnings")
        p.drawString(6 * inch, 5.6 * inch, f"${payslip.basic_salary}")
        
        # Add deductions section
        p.setFont("Helvetica-Bold", 12)
        p.drawString(1 * inch, 4.9 * inch, "Deductions")
        p.line(1 * inch, 4.8 * inch, 7 * inch, 4.8 * inch)
        p.setFont("Helvetica", 12)
        p.drawString(1 * inch, 4.5 * inch, "Income Tax")
        p.drawString(6 * inch, 4.5 * inch, f"${payslip.tax}")
        
        p.setFont("Helvetica-Bold", 12)
        p.drawString(1 * inch, 4.1 * inch, "Total Deductions")
        p.drawString(6 * inch, 4.1 * inch, f"${payslip.tax}")
        
        # Add net pay
        p.setFont("Helvetica-Bold", 14)
        p.drawString(1 * inch, 3.4 * inch, "Net Pay")
        p.drawString(6 * inch, 3.4 * inch, f"${payslip.net_pay+800}")
        
        # Add payslip details
        p.setFont("Helvetica", 10)
        p.drawString(1 * inch, 2.7 * inch, f"Payslip ID: {payslip.id}")
        p.drawString(1 * inch, 2.4 * inch, f"Generated on: {payslip.generated_on}")
        
        # Add footer
        p.setFont("Helvetica-Oblique", 10)
        p.drawString(1 * inch, 1.5 * inch, "This is a computer-generated document and does not require a signature.")
        p.drawString(1 * inch, 1.2 * inch, "For any queries regarding your salary, please contact the HR department.")
        
        # Close the PDF object cleanly, and we're done
        p.showPage()
        p.save()
        
        # Get the value of the BytesIO buffer and write it to the response
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="payslip_{month_name}_{year}.pdf"'
        
        return response
        
    except (Employee.DoesNotExist, Salary.DoesNotExist):
        return redirect("payroll")

# ---------------- Salary View ---------------- 
def salary_view(request):
    return render(request, 'salary.html')


def salary_view(request):
    return render(request, 'salary.html')

@csrf_exempt  # For testing only, use proper CSRF protection in production
def submit_salary(request):
    if request.method != "POST":
        return redirect("salary")
    
    # Get form data
    employee_id = request.POST.get("employee_id")
    basic_salary = request.POST.get("salary")
    tax_percentage = request.POST.get("tax")
    date = request.POST.get("date") or timezone.now().strftime('%Y-%m-%d')
    
    # Validate data
    if not all([employee_id, basic_salary, tax_percentage]):
        messages.error(request, "All fields are required")
        return redirect("salary")
        
    try:
        # Convert to proper data types
        employee_id = int(employee_id)
        basic_salary = Decimal(basic_salary)
        tax_percentage = Decimal(tax_percentage)
        
        # Calculate tax amount
        tax_amount = (basic_salary * tax_percentage) / Decimal('100.0')
        
        # Calculate net pay
        net_pay = basic_salary - tax_amount
        
        # Insert directly into database using raw SQL
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO salary 
                (employee_id, basic_salary, tax, net_pay, generated_on) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                [employee_id, basic_salary, tax_amount, net_pay, date]
            )
        
        messages.success(request, f"Salary of ${basic_salary} processed successfully for employee ID {employee_id}")
        return redirect("salary")
        
    except (ValueError, TypeError):
        messages.error(request, "Invalid numeric values provided")
        return redirect("salary")
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect("salary")

# ---------------- Leave View ----------------
def leave_view(request):
    user_id = request.session.get("user_id")
    try:
        employee = Employee.objects.get(id=user_id)
        if employee.check_role() == "Manager": 
            return manager_leaves_view(request)
        elif employee.check_role() == "HR":
            leave_summary = Leave.objects.annotate(
                days=ExpressionWrapper(
                   ExtractDay(F("end_date") - F("start_date")) + 1, output_field=IntegerField()
                )
            ).values("employee__department").annotate(
                annual_leave=Sum("days", filter=Q(leave_type="Annual")),
                sick_leave=Sum("days", filter=Q(leave_type="Sick")),
                personal_leave=Sum("days", filter=Q(leave_type="Personal")),
                other_leave=Sum("days", filter=Q(leave_type="Other")),
                total_days=Sum("days"),
                employee_count=Count("employee", distinct=True)
            ).order_by("employee__department")
            # Calculate average leave per employee
            for entry in leave_summary:
                entry["avg_per_employee"] = round(entry["total_days"] / entry["employee_count"], 2) if entry["employee_count"] > 0 else 0

            # Get overall totals
            totals = {
                "annual_leave": sum(entry["annual_leave"] or 0 for entry in leave_summary),
                "sick_leave": sum(entry["sick_leave"] or 0 for entry in leave_summary),
                "personal_leave": sum(entry["personal_leave"] or 0 for entry in leave_summary),
                "other_leave": sum(entry["other_leave"] or 0 for entry in leave_summary),
                "total_days": sum(entry["total_days"] or 0 for entry in leave_summary),
                "avg_per_employee": round(sum(entry["total_days"] for entry in leave_summary) / sum(entry["employee_count"] for entry in leave_summary), 2) if leave_summary else 0,
            }

            return render(request, "hr_leave.html", {
                "leave_summary": leave_summary,
                "totals": totals,
            })
        else:
            leave_requests = Leave.objects.filter(employee=employee).order_by('-requested_on')
            return render(request, "leave.html", {
                "employee": employee,
                "leave_requests": leave_requests
            })
         
    except Employee.DoesNotExist:
        return render(request, "login.html", {"error_message": "User does not exist"})
    
# ---------------- Settings View ----------------
def settings_view(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    
    employee = Employee.objects.get(id=user_id)
    return render(request, "settings.html", {"user": employee})

# ---------------- Request Leave View ----------------
def request_leave_view(request):
    """View for employees to request leave"""
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    
    try:
        employee = Employee.objects.get(id=user_id)
        
        if request.method == "POST":
            # Get form data
            leave_type = request.POST.get("leave_type")
            start_date = request.POST.get("start_date")
            end_date = request.POST.get("end_date")
            reason = request.POST.get("reason")
            
            # Validate form data
            if not all([leave_type, start_date, end_date, reason]):
                return render(request, "leave.html", {
                    "employee": employee,
                    "error_message": "All fields are required",
                    "form_data": request.POST
                })
            
            # Calculate number of days
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            days = (end - start).days + 1  
            
            # Validate date range
            if days < 1:
                return render(request, "leave.html", {
                    "employee": employee,
                    "error_message": "End date must be after start date",
                    "form_data": request.POST
                })
            
            # Save leave request
            leave = Leave(
                employee=employee,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                status="Pending",
                requested_on=timezone.now()
            )
            leave.save()
            
            # ✅ Redirect to prevent resubmission on refresh
            return redirect("request_leave_success")  # Replace with actual success page or same form page
            
        # GET request - Display form
        leave_requests = Leave.objects.filter(employee=employee).order_by('-requested_on')
        return render(request, "leave.html", {
            "employee": employee,
            "leave_requests": leave_requests
        })
        
    except Employee.DoesNotExist:
        return redirect("login")


def request_leave_success(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    
    employee = Employee.objects.get(id=user_id)
    leave_requests = Leave.objects.filter(employee=employee).order_by('-requested_on')

    return redirect("leave")
    return render(request, "leave.html", {
        "employee": employee,
        "success_message": "Leave request submitted successfully!",
        "leave_requests": leave_requests
    })

# ---------------- Manager Leave View ----------------
def manager_leaves_view(request):
    """View for administrators to see all pending leave requests"""
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    
    try:
        # Check if user is admin or HR
        employee = Employee.objects.get(id=user_id)
        if employee.check_role() not in ["Manager"]:
            messages.error(request, "You don't have permission to access this page")
            return redirect("dashboard")
        
        # Get filter parameters
        department = request.GET.get('department', '')
        leave_type = request.GET.get('leave_type', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        
        # Base query - get all pending leave requests
        pending_requests = Leave.objects.select_related('employee')
        
        # Apply filters if provided
        if department:
            pending_requests = pending_requests.filter(employee__department=department)
        
        if leave_type:
            pending_requests = pending_requests.filter(leave_type=leave_type)
        
        if date_from:
            pending_requests = pending_requests.filter(start_date__gte=date_from)
        
        if date_to:
            pending_requests = pending_requests.filter(end_date__lte=date_to)
        
        for leave in pending_requests:
            # If days field doesn't already exist
            if not hasattr(leave, 'days') or leave.days is None:
                start = leave.start_date
                end = leave.end_date
                leave.days = (end - start).days + 1  # Include both start and end days

        # Get unique departments and leave types for filter dropdowns
        departments = Employee.objects.values_list('department', flat=True).distinct()
        leave_types = Leave.objects.values_list('leave_type', flat=True).distinct()
        
        # Get counts for dashboard stats
        pending_count = Leave.objects.filter(status="Pending").count()
        approved_count = Leave.objects.filter(status="Approved").count()
        rejected_count = Leave.objects.filter(status="Rejected").count()
        
        # Get employees currently on leave (approved leaves that include today's date)
        from django.utils import timezone
        today = timezone.now().date()
        on_leave_count = Leave.objects.filter(
            status="Approved",
            start_date__lte=today,
            end_date__gte=today
        ).count()
        
        context = {
            'employee': employee,
            'pending_requests': pending_requests,
            'departments': departments,
            'leave_types': leave_types,
            'filters': {
                'department': department,
                'leave_type': leave_type,
                'date_from': date_from,
                'date_to': date_to,
            },
            'stats': {
                'pending_count': pending_count,
                'approved_count': approved_count,
                'rejected_count': rejected_count,
                'on_leave_count': on_leave_count,
            }
        }
        
        return render(request, "manager_leave.html", context)
        
    except Employee.DoesNotExist:
        return redirect("login")
    

def leave_action_view(request, leave_id, action):
    """View for approving or rejecting leave requests"""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)
    
    user_id = request.session.get("user_id")
    if not user_id:
        return JsonResponse({"error": "User not authenticated"}, status=401)

    try:
        # Check if user is a Manager
        employee = Employee.objects.get(id=user_id)
        if employee.check_role() != "Manager":
            return JsonResponse({"error": "You don't have permission to perform this action"}, status=403)

        # Get the leave request
        leave_request = get_object_or_404(Leave, id=leave_id)

        # Check if leave is already processed
        if leave_request.status != "Pending":
            return JsonResponse({"message": f"This leave request has already been {leave_request.status.lower()}."}, status=400)

        # Process the action
        if action == "approve":
            leave_request.status = "Approved"
            success_message = "Leave request approved successfully."
        elif action == "reject":
            leave_request.status = "Rejected"
            success_message = "Leave request rejected successfully."
        else:
            return JsonResponse({"error": "Invalid action"}, status=400)

        
        # Update approval details
        leave_request.manager = employee
        leave_request.approved_on = timezone.now()
        leave_request.save()

        return JsonResponse({"success": True, "message": success_message})

    except Employee.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    except Leave.DoesNotExist:
        return JsonResponse({"error": "Leave request not found"}, status=404)


def leave_summary_view(request):
    """View to display leave summary by department."""
    
    # Get all leave requests, grouped by department


def get_leave_report(request):
    department = request.GET.get("department", "all")
    leave_type = request.GET.get("leave_type", "all")

    # Calculate leave duration in days
    leave_duration = ExpressionWrapper(
        ExtractDay(F("end_date") - F("start_date")) + 1,
        output_field=IntegerField()
    )

    # Apply filters
    filters = Q()
    if department != "all":
        filters &= Q(employee__department=department)
    if leave_type != "all":
        filters &= Q(leave_type__iexact=leave_type)

    # Fetch filtered leave data
    report_data = (
        Leave.objects.filter(filters)
        .values("employee__department")
        .annotate(
            annual_leave=Sum(leave_duration, filter=Q(leave_type="Annual")),
            sick_leave=Sum(leave_duration, filter=Q(leave_type="Sick")),
            personal_leave=Sum(leave_duration, filter=Q(leave_type="Personal")),
            other_leave=Sum(leave_duration, filter=Q(leave_type="Other")),
            total_days=Sum(leave_duration),
            employee_count=Count("employee", distinct=True),
        )
    )

    result = []
    total_annual_leave = 0
    total_sick_leave = 0
    total_personal_leave = 0
    total_other_leave = 0
    total_days = 0
    total_employees = 0

    for item in report_data:
        annual_leave = item["annual_leave"] or 0
        sick_leave = item["sick_leave"] or 0
        personal_leave = item["personal_leave"] or 0
        other_leave = item["other_leave"] or 0
        total_leave_days = item["total_days"] or 0
        employee_count = item["employee_count"] or 0

        result.append({
            "department": item["employee__department"],
            "annual_leave": annual_leave,
            "sick_leave": sick_leave,
            "personal_leave": personal_leave,
            "other_leave": other_leave,
            "total_days": total_leave_days,
            "avg_per_employee": round(total_leave_days / employee_count, 2) if employee_count else 0,
        })

        # Accumulate totals
        total_annual_leave += annual_leave
        total_sick_leave += sick_leave
        total_personal_leave += personal_leave
        total_other_leave += other_leave
        total_days += total_leave_days
        total_employees += employee_count

    # Create a totals dictionary
    totals = {
        "annual_leave": total_annual_leave,
        "sick_leave": total_sick_leave,
        "personal_leave": total_personal_leave,
        "other_leave": total_other_leave,
        "total_days": total_days,
        "avg_per_employee": round(total_days / total_employees, 2) if total_employees else 0,
    }

    return JsonResponse({"report": result, "totals": totals}, safe=False)




def update_profile_pass(request):
    if request.method == 'POST':
        employee_id = request.session.get("user_id")

        try:
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('settings')

        # Get form data
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        # Verify current password
        if not check_password(current_password, employee.password):
            messages.error(request, "Current password is incorrect.")
            return redirect('settings')

        # Validate new password
        if new_password != confirm_password:
            messages.error(request, "New password and confirmation do not match.")
            return redirect('settings')

       
        # Update password
        employee.password = make_password(new_password)  # Hash the password
        employee.save()

        messages.success(request, "Password updated successfully.")
        return redirect('settings')

    return render(request, 'settings.html', {"user": employee})


login_required
def employee_manage_view(request):
    # Check if the user is an admin
    try:
        employee = request.user.employee
        if employee.role != 'Admin':
            messages.error(request, 'You do not have permission to access this page')
            return redirect('dashboard')
    except Employee.DoesNotExist:
        messages.error(request, 'Employee profile not found')
        logout(request)
        return redirect('login')
    
    # Get all employees except admins
    employees = Employee.objects.exclude(role='Admin').select_related('user')
    
    context = {
        'employees': employees,
    }
    
    return render(request, 'employee_manage.html', context)

@login_required
def update_employee_role(request, employee_id):
    # Check if the user is an admin
    try:
        current_employee = request.user.employee
        if current_employee.role != 'Admin':
            messages.error(request, 'You do not have permission to perform this action')
            return redirect('dashboard')
    except Employee.DoesNotExist:
        messages.error(request, 'Employee profile not found')
        logout(request)
        return redirect('login')
    
    if request.method == 'POST':
        try:
            # Get the employee to update
            employee = Employee.objects.get(id=employee_id)
            
            # Get the new role from the form
            new_role = request.POST.get('role')
            
            # Validate the role
            valid_roles = ['HR', 'Manager', 'Employee']
            if new_role not in valid_roles:
                messages.error(request, 'Invalid role selected')
                return redirect('employee_manage')
            
            # Update the employee's role
            employee.role = new_role
            employee.save()
            
            messages.success(request, f'Role updated successfully for {employee.user.get_full_name()}')
        except Employee.DoesNotExist:
            messages.error(request, 'Employee not found')
        except Exception as e:
            messages.error(request, f'Error updating role: {str(e)}')
    
    return redirect('employee_manage')

@login_required
def get_employee_details(request, employee_id):
    # Check if the user is an admin
    try:
        current_employee = request.user.employee
        if current_employee.role != 'Admin':
            return JsonResponse({'error': 'Permission denied'}, status=403)
    except Employee.DoesNotExist:
        return JsonResponse({'error': 'Employee profile not found'}, status=404)
    
    try:
        # Get the employee details
        employee = Employee.objects.select_related('user').get(id=employee_id)
        
        # Create a dictionary with employee details
        employee_data = {
            'id': employee.id,
            'employee_id': employee.employee_id,
            'name': employee.user.get_full_name(),
            'email': employee.user.email,
            'department': employee.department,
            'position': employee.position or '',
            'role': employee.role,
            'phone': employee.phone or '',
            'address': employee.address or '',
            'join_date': employee.join_date.strftime('%Y-%m-%d') if employee.join_date else '',
            'emergency_contact_name': employee.emergency_contact_name or '',
            'emergency_contact_phone': employee.emergency_contact_phone or '',
            'emergency_contact_relation': employee.emergency_contact_relation or '',
        }
        
        return JsonResponse(employee_data)
    except Employee.DoesNotExist:
        return JsonResponse({'error': 'Employee not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def employee_view(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    
    employees = Employee.objects.all().order_by('id')
    emp = Employee.objects.get(id = user_id)
    print(emp)
    return render(request, "employee.html", {"users": employees, "user": emp})



def update_profile_image(request):
    if request.method == 'POST':
        try:
            # Get the employee from the session
            user_id = request.session.get('user_id')
            if not user_id:
                messages.error(request, "You must be logged in to update your profile image.")
                return redirect('login')
            
            employee = Employee.objects.get(id=user_id)
            
            # Get the image data from the form
            image_data = request.POST.get('image_data')
            
            if image_data:
                try:
                    # Remove the data:image/jpeg;base64, part
                    format, imgstr = image_data.split(';base64,')
                    ext = format.split('/')[-1]
                    
                    # Generate a filename
                    filename = f"profile_{employee.id}.{ext}"
                    
                    # Convert base64 to file
                    data = ContentFile(base64.b64decode(imgstr), name=filename)
                    
                    # Delete old image if it exists
                    if employee.profile_image:
                        if os.path.isfile(employee.profile_image.path):
                            os.remove(employee.profile_image.path)
                    
                    # Save new image
                    employee.profile_image = data
                    employee.save()
                    
                    messages.success(request, "Profile image updated successfully!")
                except Exception as e:
                    messages.error(request, f"Error processing image: {str(e)}")
            else:
                messages.error(request, "No image data received.")
                
            return redirect('dashboard')
            
        except Employee.DoesNotExist:
            messages.error(request, "Employee not found.")
            return redirect('login')
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    return redirect('dashboard')


import re 
def update_employee(request):
    if request.method == 'POST':
        try:
            employee = Employee.objects.get(id=request.POST.get('employee_id'))  # Fetch user by email
        except Employee.DoesNotExist:
            return redirect('employee')
        
        
        # Ensure the user is authenticated
        try:
            full_name = request.POST.get('name', '')
            if full_name:
                name_parts = full_name.strip().split(' ', 1)  # split into first and last
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''

                # Regex: Only allow letters and spaces (you can modify to include hyphens or apostrophes if needed)
                name_pattern = r'^[A-Za-z]+$'

                if not re.fullmatch(name_pattern, first_name):
                    messages.error(request, "First name must contain only letters.")
                    return redirect('employee')

                if last_name and not re.fullmatch(name_pattern, last_name):
                    messages.error(request, "Last name must contain only letters.")
                    return redirect('employee')

                employee.first_name = first_name
                employee.last_name = last_name    
            employee.email = request.POST.get('email', employee.email)
            employee.save()
        except Exception as e:
            messages.error(request, f"Error updating employee: {str(e)}")

        logged_employee_id = request.session.get("user_id")
        logged_employee = Employee.objects.get(id=logged_employee_id)

        employees = Employee.objects.all()
        return redirect("employee")


def update_profile(request):

    print("Hiiii")
    if request.method == 'POST':
        employee_id = request.session.get("user_id")
    
        print("Emp ", employee_id)
        try:
            employee = Employee.objects.get(id=employee_id)  # Fetch user by email
        except Employee.DoesNotExist:
            return redirect('settings')
        
        # Ensure the user is authenticated
        try:
            first_name = request.POST.get('first_name', employee.first_name)
            last_name = request.POST.get('last_name', employee.last_name)
            name_pattern = r'^[A-Za-z]+$'

            if not re.fullmatch(name_pattern, first_name):
                messages.error(request, "First name must contain only letters.")
                return redirect('settings')

            if last_name and not re.fullmatch(name_pattern, last_name):
                messages.error(request, "Last name must contain only letters.")
                return redirect('settings')
            
            employee.email = request.POST.get('email', employee.email)
            employee.save()
        except Exception as e:
            messages.error(request, f"Error updating employee: {str(e)}")

    return render(request, 'settings.html', {"user": employee})

def cancel_leave_view(request, leave_id):
    leave = Leave.objects.get(id=leave_id)
    if not leave:
        messages.error(request, 'Leave request not found.')
        return redirect('leave')

    leave.delete()  # Permanently remove the leave request from the DB
    messages.success(request, 'Leave request cancelled successfully.')
    return redirect('leave')  # Redirect to the leave page