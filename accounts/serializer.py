# class AuthTokenObtainPairSerializer(TokenObtainPairSerializer):

#     @classmethod
#     def get_token(cls, user):

#         token = super(AuthTokenObtainPairSerializer, cls).get_token(user)

#         token['email'] = user.email
#         return token



# class SignupSerializer(serializers.ModelSerializer):

#     email = serializers.EmailField(
#             required=True,
#             validators=[UniqueValidator(queryset=User.objects.all())]
#             )

#     password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
#     password2 = serializers.CharField(write_only=True, required=True)

#     class Meta:
#         model = User
#         fields = ('email', 'first_name', 'last_name', 'password', 'password2')
#         extra_kwargs = {
#             'email' : {'required' : True},
#             'first_name': {'required': True},
#             'last_name': {'required': True}
#         }

#     def validate(self, attrs):
#         if attrs['password'] != attrs['password2']:
#             raise serializers.ValidationError({"password": "Password fields didn't match."})

#         return attrs

#     def create(self, validated_data):
#         user = User.objects.create(
#             email=validated_data['email'],
#             first_name=validated_data['first_name'],
#             last_name=validated_data['last_name']
#         )

        
#         user.set_password(validated_data['password'])
#         user.save()

#         return user
    

# class UserSerializer(serializers.ModelSerializer):
#     country = serializers.CharField(source='country.name', required=False)

#     class Meta:
#         model = User
#         fields = [
#             'id', 'avatar', 'email', 'email_confirmed', 'access_code', 'first_name',
#             'last_name', 'dob', 'nrc', 'country', 'phone', 'is_staff', 'location',
#             'date_joined', 'is_active', 'is_verified', 'creation_ip_address',
#             'deletion_ip_address'
#         ]

#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         if instance.country:
#             representation['country'] = instance.country.name
#         return representation