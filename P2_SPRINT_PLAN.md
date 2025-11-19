# P2 Sprint – Edge Case Szenáriók & Folyamat-tesztelés

**Sprint Duration**: 7-10 nap
**Priority**: P2 - Medium (Production Readiness Validation)
**Status**: 🚧 In Progress

---

## 🎯 Sprint Cél

**Teljes körű megbízhatósági garancia biztosítása** edge case-ek, stressz tesztek és recovery szenáriók lefedésével.

**Miért most?**
- P0 ✅ kritikus hibák javítva
- P1 ✅ automatizálás és stabilizálás kész
- P2 → Validáljuk, hogy a rendszer **valós körülmények** között is működik

---

## 📋 Feladatok (Tasks)

### 1️⃣ Sync Edge Case Szenáriók Teszt Csomag

**Fájl**: `app/tests/test_sync_edge_cases.py`

**Tesztelendő Szcenáriók**:

| Szcenárió | Leírás | Elvárás |
|-----------|--------|---------|
| **Félbeszakadt License Upgrade** | Transaction félbeszakad `advance_license()` közben | Rollback, nincs partial update |
| **Concurrent Level Up** | 2 session egyszerre próbál level up-olni | Csak 1 sikeres, másik conflict error |
| **Orphan Progress Created** | User törlése FK constraint előtt | FK constraint megakadályozza |
| **License Without Progress** | Admin létrehoz licenszt progress nélkül | Auto-sync létrehozza a progresst |
| **Progress Without License** | Student level up-ol, nincs license | Auto-sync létrehozza a licenszt |
| **Desync After Rollback** | Progress committed, license rollback | Background job kijavítja |
| **Max Level Overflow** | Próbál level 9-re lépni (max=8) | Validation megakadályozza |
| **Negative XP** | Próbál negatív XP-t adni | Validation megakadályozza |
| **Duplicate Auto-Sync** | 2 hook egyszerre triggerel | Idempotent, nem duplikál |

**Implementáció**:
```python
class SyncEdgeCaseTester:
    def test_interrupted_license_upgrade(self):
        """Simulate transaction rollback during license upgrade"""

    def test_concurrent_level_up(self):
        """Simulate race condition with 2 sessions"""

    def test_orphan_prevention(self):
        """Verify FK constraints prevent orphans"""

    # ... további edge case-ek
```

**Eredmény**: Teljes edge case lefedettség dokumentálva

---

### 2️⃣ Desync Recovery Stress Test (10,000 User)

**Fájl**: `app/tests/stress/test_desync_recovery.py`

**Cél**: Nagy volumenű adattal tesztelni a sync mechanizmust

**Process**:
1. Generálj 10,000 test usert
2. Szándékosan hozz létre desync-et minden 10. usernél (1,000 desync)
3. Futtasd `auto_sync_all()`
4. Mérj: duration, success rate, memory usage

**Metrikák**:
```python
{
    "total_users": 10000,
    "desync_count": 1000,
    "sync_duration_seconds": X,
    "success_rate": Y%,
    "memory_peak_mb": Z,
    "avg_sync_time_per_user_ms": W
}
```

**Elfogadási Kritériumok**:
- ✅ Success rate ≥ 99%
- ✅ Sync duration < 60 seconds
- ✅ Memory peak < 500 MB
- ✅ No DB connection leaks

---

### 3️⃣ Orphan Record Recovery Script

**Fájl**: `scripts/recovery/orphan_recovery.py`

**Cél**: Ha manuális DB művelet orphan rekordokat hozott létre (FK előtt), javítsa ki

**Funkciók**:
```python
class OrphanRecoveryTool:
    def find_orphan_progress_records(self):
        """Find progress without valid user or specialization"""

    def find_orphan_license_records(self):
        """Find licenses without valid user or specialization"""

    def fix_or_delete_orphans(self, dry_run=True):
        """Delete orphan records or attempt to fix"""

    def generate_report(self):
        """Create detailed report of orphans found/fixed"""
```

**Safety Features**:
- ✅ Default `dry_run=True`
- ✅ Backup before deletion
- ✅ Detailed report with undo script
- ✅ Admin approval required for actual deletion

---

### 4️⃣ Scheduler 24-Hour Logging Stress Test

**Fájl**: `app/tests/stress/test_scheduler_24h.py`

**Cél**: Scheduler stabilitás validálása hosszú futás alatt

**Process**:
1. Módosítsd a scheduler interval-t 10 percre (gyorsított teszt)
2. Futtasd 24 órán keresztül (144 job execution)
3. Monitor:
   - Memory leaks
   - Log file sizes
   - Job execution time drift
   - Error rates

**Automatizált Check**:
```python
def validate_24h_logs():
    """Analyze 24h of scheduler logs"""
    logs = parse_sync_logs("logs/sync_jobs/")

    assert no_memory_leak(logs)
    assert avg_job_duration_stable(logs)
    assert no_job_failures(logs)
    assert log_files_rotated_properly(logs)
```

**Eredmény**: Garantált scheduler stabilitás production-ben

---

### 5️⃣ Rollback & Recovery Szcenáriók

**Fájl**: `app/tests/test_rollback_recovery.py`

**Tesztelendő**:

| Szcenárió | Trigger | Recovery |
|-----------|---------|----------|
| **Progress Rollback** | DB error during commit | Transaction rollback, no partial data |
| **License Rollback** | Validation fails mid-advancement | No license change, progression not created |
| **Sync Rollback** | Sync fails after progress commit | Progress remains, sync retried by background job |
| **Migration Rollback** | Downgrade migration | FK constraints removed safely |

**Implementáció**:
```python
class RollbackRecoveryTester:
    def test_progress_rollback_on_db_error(self):
        """Simulate DB error during progress update"""
        with pytest.raises(SQLAlchemyError):
            service.update_progress(...)

        # Verify no partial update
        assert progress.current_level == original_level

    def test_license_rollback_on_validation_fail(self):
        """Simulate validation failure during advancement"""
        result = service.advance_license(target_level=999)

        assert result["success"] == False
        assert license.current_level == original_level
```

---

### 6️⃣ Performance Benchmarking

**Fájl**: `app/tests/benchmarks/sync_performance.py`

**Mérések**:

| Művelet | Target | Mért |
|---------|--------|------|
| `sync_progress_to_license()` | < 50ms | ? |
| `sync_license_to_progress()` | < 50ms | ? |
| `find_desync_issues()` (10k users) | < 5s | ? |
| `auto_sync_all()` (100 desync) | < 10s | ? |
| Background job (typical load) | < 30s | ? |

**Tools**:
- `pytest-benchmark`
- `memory_profiler`
- Custom timing decorators

---

## 📊 Success Metrics (Sprint Done Definition)

| Metric | Target | Priority |
|--------|--------|----------|
| Edge case test coverage | ≥ 90% | P0 |
| Stress test success rate | ≥ 99% | P0 |
| Orphan records found | 0 | P1 |
| 24h scheduler uptime | 100% | P0 |
| Memory leak incidents | 0 | P0 |
| Rollback safety | 100% | P0 |
| Performance benchmarks met | ≥ 80% | P1 |

---

## 🧪 Test Execution Plan

### Day 1-2: Edge Case Test Suite
- Implementálj minden edge case tesztet
- Futtasd és dokumentáld az eredményeket
- Javítsd a fellelt bugokat

### Day 3-4: Stress Testing
- 10k user desync test
- 24h scheduler test (gyorsított módban)
- Performance benchmarking

### Day 5-6: Recovery Tools
- Orphan recovery script
- Rollback tests
- Safety validations

### Day 7: Validation & Reporting
- Összesített riport
- Metrics review
- Production readiness checklist

---

## 📁 Új Fájlstruktúra

```
app/
 ├── tests/
 │   ├── test_sync_edge_cases.py (új)
 │   ├── test_rollback_recovery.py (új)
 │   ├── stress/
 │   │   ├── __init__.py
 │   │   ├── test_desync_recovery.py (új)
 │   │   └── test_scheduler_24h.py (új)
 │   └── benchmarks/
 │       ├── __init__.py
 │       └── sync_performance.py (új)
 │
 └── scripts/
     └── recovery/
         ├── __init__.py
         └── orphan_recovery.py (új)

logs/
 └── stress_tests/ (új)
     ├── desync_10k_YYYYMMDD.log
     ├── scheduler_24h_YYYYMMDD.log
     └── benchmarks_YYYYMMDD.json
```

---

## 🎯 Várható Eredmények

### Technikai
- ✅ Teljes edge case lefedettség
- ✅ Validált stress test capacity (10k+ users)
- ✅ Orphan record prevention & recovery
- ✅ 24/7 scheduler reliability
- ✅ Performance baseline metrics

### Üzleti
- ✅ Production readiness garancia
- ✅ Skálázhatósági bizonyíték
- ✅ Disaster recovery terv
- ✅ SLA-ready monitoring

### Dokumentáció
- ✅ Edge case playbook
- ✅ Recovery runbook
- ✅ Performance benchmark report
- ✅ P2 validation report

---

## 🚀 Post-Sprint Actions

Ha P2 sikeres:
1. ✅ **Go-Live Decision Point** - Production deployment engedélyezése
2. → P3 Sprint (Monitoring + Teljesítmény-optimalizálás)
3. → Funkcionális bővítések (új features)

Ha P2 során problémákat találunk:
1. ⚠️ **Fix Critical Issues** azonnal
2. → Re-run failed tests
3. → Update P2 report

---

**Sprint Owner**: Claude Code
**Status**: 🚧 Ready to Start
**Next Step**: Implementálni az első edge case test suite-ot
