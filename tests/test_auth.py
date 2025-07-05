import pytest
import os
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from services.app.auth import (
    verify_password, get_password_hash, create_access_token, verify_token,
    get_current_user, get_current_active_user, SECRET_KEY, ALGORITHM
)
from services.app.models import User

class TestPasswordHashing:
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert verify_password(password, hashed)
    
    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes"""
        password1 = "password1"
        password2 = "password2"
        
        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)
        
        assert hash1 != hash2
    
    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (salt)"""
        password = "test_password_123"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

class TestTokenGeneration:
    
    def test_create_access_token(self):
        """Test creating an access token"""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
        assert "exp" in payload
    
    def test_create_access_token_with_expiry(self):
        """Test creating an access token with custom expiry"""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=60)
        token = create_access_token(data, expires_delta)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check expiry time
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        expected_exp = datetime.utcnow() + expires_delta
        
        # Allow for small time differences
        assert abs((exp_time - expected_exp).total_seconds()) < 60
    
    def test_create_access_token_default_expiry(self):
        """Test creating an access token with default expiry"""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check default expiry (30 minutes)
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        expected_exp = datetime.utcnow() + timedelta(minutes=30)
        
        # Allow for small time differences
        assert abs((exp_time - expected_exp).total_seconds()) < 60

class TestTokenVerification:
    
    def test_verify_valid_token(self):
        """Test verifying a valid token"""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "testuser"
    
    def test_verify_invalid_token(self):
        """Test verifying an invalid token"""
        invalid_token = "invalid.token.here"
        
        payload = verify_token(invalid_token)
        
        assert payload is None
    
    def test_verify_expired_token(self):
        """Test verifying an expired token"""
        data = {"sub": "testuser"}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta)
        
        payload = verify_token(token)
        
        assert payload is None
    
    def test_verify_malformed_token(self):
        """Test verifying a malformed token"""
        malformed_tokens = [
            "",
            "not.a.token",
            "Bearer invalid",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # Incomplete token
        ]
        
        for token in malformed_tokens:
            payload = verify_token(token)
            assert payload is None

class TestUserAuthentication:
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        mock_db = Mock()
        return mock_db
    
    @pytest.fixture
    def mock_user(self):
        """Mock user object"""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.is_active = True
        user.hashed_password = get_password_hash("testpassword")
        return user
    
    def test_get_current_user_valid_token(self, mock_db_session, mock_user):
        """Test getting current user with valid token"""
        # Create token
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        # Mock database query
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('services.app.auth.get_db', return_value=mock_db_session):
            user = get_current_user(token, mock_db_session)
            
            assert user == mock_user
            assert user.username == "testuser"
    
    def test_get_current_user_invalid_token(self, mock_db_session):
        """Test getting current user with invalid token"""
        invalid_token = "invalid.token"
        
        with patch('services.app.auth.get_db', return_value=mock_db_session):
            with pytest.raises(Exception):  # Should raise HTTPException
                get_current_user(invalid_token, mock_db_session)
    
    def test_get_current_user_user_not_found(self, mock_db_session):
        """Test getting current user when user not found in database"""
        # Create valid token
        data = {"sub": "nonexistentuser"}
        token = create_access_token(data)
        
        # Mock database query to return None
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        with patch('services.app.auth.get_db', return_value=mock_db_session):
            with pytest.raises(Exception):  # Should raise HTTPException
                get_current_user(token, mock_db_session)
    
    def test_get_current_active_user_active(self, mock_user):
        """Test getting current active user with active user"""
        mock_user.is_active = True
        
        result = get_current_active_user(mock_user)
        
        assert result == mock_user
    
    def test_get_current_active_user_inactive(self, mock_user):
        """Test getting current active user with inactive user"""
        mock_user.is_active = False
        
        with pytest.raises(Exception):  # Should raise HTTPException
            get_current_active_user(mock_user)

class TestSecurityConfiguration:
    
    def test_secret_key_exists(self):
        """Test that secret key is configured"""
        assert SECRET_KEY is not None
        assert len(SECRET_KEY) > 0
    
    def test_algorithm_configuration(self):
        """Test that algorithm is properly configured"""
        assert ALGORITHM == "HS256"
    
    def test_password_context_configuration(self):
        """Test that password context is properly configured"""
        # Test that we can hash and verify passwords
        password = "test_password"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)

class TestEnvironmentSpecificBehavior:
    
    def test_testing_mode_password_hashing(self):
        """Test password hashing in testing mode"""
        with patch.dict(os.environ, {"TESTING": "1"}):
            # Import auth module fresh to pick up testing mode
            import importlib
            import services.app.auth
            importlib.reload(services.app.auth)
            
            # Test that password hashing still works
            password = "test_password"
            hashed = services.app.auth.get_password_hash(password)
            
            assert services.app.auth.verify_password(password, hashed)
    
    def test_production_mode_password_hashing(self):
        """Test password hashing in production mode"""
        with patch.dict(os.environ, {"TESTING": "0"}):
            # Import auth module fresh to pick up production mode
            import importlib
            import services.app.auth
            importlib.reload(services.app.auth)
            
            # Test that password hashing still works
            password = "test_password"
            hashed = services.app.auth.get_password_hash(password)
            
            assert services.app.auth.verify_password(password, hashed)

class TestTokenEdgeCases:
    
    def test_token_with_additional_claims(self):
        """Test creating and verifying token with additional claims"""
        data = {
            "sub": "testuser",
            "role": "admin",
            "permissions": ["read", "write"]
        }
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload["sub"] == "testuser"
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]
    
    def test_token_with_unicode_data(self):
        """Test creating token with unicode data"""
        data = {"sub": "用户名", "name": "José María"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload["sub"] == "用户名"
        assert payload["name"] == "José María"
    
    def test_very_long_token_data(self):
        """Test creating token with large amount of data"""
        data = {
            "sub": "testuser",
            "large_data": "x" * 1000,  # 1000 character string
            "permissions": ["permission_" + str(i) for i in range(100)]
        }
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload["sub"] == "testuser"
        assert len(payload["large_data"]) == 1000
        assert len(payload["permissions"]) == 100