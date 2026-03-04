from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django import forms
from .models import User, Contact
from django.contrib.auth import authenticate



class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')




class CustomAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form
    """
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                raise ValidationError("Invalid email or password.")
            else:
                self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data
    
class UserProfileForm(forms.ModelForm):
    """
    Form for user profile editing
    """
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone_number', 'profile_pic')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_pic': forms.FileInput(attrs={'class': 'form-control'}),
        }

class AdminUserCreationForm(UserCreationForm):
    """
    Form for admin to create users with user type selection
    """
    user_type = forms.ChoiceField(
        choices=User.USER_TYPE,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone_number', 'user_type', 
                 'profile_pic', 'is_active', 'is_staff')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_pic': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ('name', 'email', 'phone', 'message')