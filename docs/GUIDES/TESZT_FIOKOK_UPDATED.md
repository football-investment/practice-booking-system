# Teszt Fiókok - FRISSÍTVE 2025-12-15

## Instructor Fiók

```
Email:    grandmaster@lfa.com
Jelszó:   grandmaster2024
```

**FONTOS**: A jelszó frissítve lett 2025-12-15-én!

## Student Fiók

```
Email:    junior.intern@lfa.com
Jelszó:   junior123
```

## Admin Fiók

```
Email:    admin@yourcompany.com
Jelszó:   admin123
```

---

## API Teszt Parancsok

### Instructor Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"grandmaster@lfa.com","password":"grandmaster2024"}'
```

### Student Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"junior.intern@lfa.com","password":"junior123"}'
```
