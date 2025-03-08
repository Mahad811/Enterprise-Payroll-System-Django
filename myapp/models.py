from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password


class Salary(models.Model):
    employee_id = models.IntegerField()  # Simple integer field instead of ForeignKey
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_pay = models.DecimalField(max_digits=10, decimal_places=2)
    generated_on = models.DateField(default=timezone.now)
    
    def __str__(self):
        return f"Employee ID: {self.employee_id} - ${self.basic_salary}"
    
    class Meta:
        db_table = "salary"  # Match the PostgreSQL table name

class Employee(models.Model):
    ROLE_CHOICES = (
        ('Admin', 'Admin'),
        ('HR', 'HR'),
        ('Manager', 'Manager'),
        ('Employee', 'Employee'),
    )

    first_name = models.CharField(max_length=50, default="user")
    last_name = models.CharField(max_length=50, default="khan")
    email = models.EmailField(unique=True, default="default@email.com")
    password = models.CharField(max_length=255, default="defaultpassword")  # Store hashed password
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Employee')
    department = models.CharField(max_length=50, blank=True, null=True)
    date_joined = models.DateField(auto_now_add=True)
    # Add profile image field
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
        
    def set_password(self, raw_password):
        """Hashes and sets the password"""
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Checks password validity"""
        return check_password(raw_password, self.password)
    
    def get_full_name(self):
        """Returns the full name of the employee"""
        return f"{self.first_name} {self.last_name}"
    
    def check_role(self):
        return self.role

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"
    
class Leave(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )

    leave_type = models.CharField(max_length=50)
    employee = models.ForeignKey('myapp.Employee', on_delete=models.CASCADE, related_name="leaves")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    manager = models.ForeignKey('myapp.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_leaves")
    requested_on = models.DateField(auto_now_add=True)
    approved_on = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "myapp_leaves" 

    def approve(self, manager):
        """Approve the leave request"""
        self.status = 'Approved'
        self.manager = manager
        self.approved_on = now().date()
        self.save()

    def reject(self, manager):
        """Reject the leave request"""
        self.status = 'Rejected'
        self.manager = manager
        self.save()

    def __str__(self):
        return f"{self.employee.first_name} {self.employee.last_name} - {self.leave_type} ({self.status})"
    


