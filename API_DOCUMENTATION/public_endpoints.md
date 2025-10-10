# 🔓 PUBLIC API ENDPOINTS

**Access Level**: No Authentication Required  
**Base URL**: `http://localhost:8000/api/v1/`

---

## 🔐 AUTHENTICATION ENDPOINTS

### POST `/auth/login`
- **Purpose**: User authentication with JSON credentials
- **Access Level**: Public
- **Request Body**: 
  ```json
  {
    "email": "string",
    "password": "string"
  }
  ```
- **Response**: 
  ```json
  {
    "access_token": "string",
    "refresh_token": "string", 
    "token_type": "bearer"
  }
  ```
- **Error Codes**: 
  - `401` - Invalid credentials
  - `400` - Inactive user account
- **Security**: Password verification with bcrypt hashing

---

### POST `/auth/login/form`
- **Purpose**: OAuth2-compatible form-based authentication
- **Access Level**: Public
- **Request Body**: Form data (`application/x-www-form-urlencoded`)
  ```
  username=email@domain.com
  password=userpassword
  ```
- **Response**: Same as `/auth/login`
- **Error Codes**: Same as `/auth/login`
- **Security**: Compatible with OAuth2 password flow

---

### POST `/auth/refresh`
- **Purpose**: Refresh expired access token using refresh token
- **Access Level**: Public (but requires valid refresh token)
- **Request Body**:
  ```json
  {
    "refresh_token": "string"
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "string",
    "refresh_token": "string",
    "token_type": "bearer"
  }
  ```
- **Error Codes**:
  - `401` - Invalid or expired refresh token
  - `400` - Malformed token
- **Security**: JWT validation with signature verification

---

## 🔒 SECURITY CONSIDERATIONS

1. **Rate Limiting**: Authentication endpoints should implement rate limiting
2. **Token Expiration**: 
   - Access tokens: 30 minutes (configurable)
   - Refresh tokens: 7 days (configurable)
3. **Password Requirements**: Enforced at application level
4. **Account Lockout**: Consider implementing after failed attempts
5. **HTTPS Required**: All authentication must use HTTPS in production

---

## 🧪 TESTING EXAMPLES

### Successful Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpassword"}'
```

### Token Refresh
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"your_refresh_token_here"}'
```

---

**Note**: These are the only endpoints that don't require authentication. All other system endpoints require a valid JWT Bearer token.