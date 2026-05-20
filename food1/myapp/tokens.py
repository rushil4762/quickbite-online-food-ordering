from django.contrib.auth.tokens import PasswordResetTokenGenerator

class ProfileTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, profile, timestamp):
        return f"{profile.pk}{timestamp}"

profile_token_generator = ProfileTokenGenerator()
