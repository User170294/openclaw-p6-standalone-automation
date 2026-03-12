from __future__ import annotations

import sqlite3
import sys
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_CORE = ROOT / 'scripts' / 'core'
if str(SCRIPTS_CORE) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_CORE))

import pv_engine  # noqa: E402


CALENDAR_WEEKDAYS = r"""(0||CalendarData()(
  (0||DaysOfWeek()(
    (0||1()())
    (0||2()(
      (0||0(s|08:00|f|13:00)())
      (0||1(s|14:00|f|18:00)())))
    (0||3()(
      (0||0(s|08:00|f|13:00)())
      (0||1(s|14:00|f|18:00)())))
    (0||4()(
      (0||0(s|08:00|f|13:00)())
      (0||1(s|14:00|f|18:00)())))
    (0||5()(
      (0||0(s|08:00|f|13:00)())
      (0||1(s|14:00|f|18:00)())))
    (0||6()(
      (0||0(s|08:00|f|13:00)())
      (0||1(s|14:00|f|18:00)())))
    (0||7()())))
  (0||Exceptions()())))"""


def _create_schema(cur):
    cur.execute(
        '''
        CREATE TABLE TASKRSRC (
            PROJ_ID INTEGER,
            TASK_ID INTEGER,
            RSRC_TYPE TEXT,
            TARGET_QTY REAL,
            TARGET_START_DATE TEXT,
            TARGET_END_DATE TEXT,
            ACT_REG_QTY REAL,
            ACT_OT_QTY REAL,
            ACT_START_DATE TEXT,
            ACT_END_DATE TEXT
        )
        '''
    )
    cur.execute(
        '''
        CREATE TABLE TASK (
            PROJ_ID INTEGER,
            TASK_ID INTEGER,
            CLNDR_ID INTEGER
        )
        '''
    )
    cur.execute(
        '''
        CREATE TABLE CALENDAR (
            CLNDR_ID INTEGER,
            CLNDR_NAME TEXT,
            CLNDR_DATA TEXT
        )
        '''
    )


def _build_fake_db(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        cur = con.cursor()
        _create_schema(cur)
        cur.execute('INSERT INTO CALENDAR (CLNDR_ID, CLNDR_NAME, CLNDR_DATA) VALUES (?,?,?)', (100, 'Weekdays', CALENDAR_WEEKDAYS))
        cur.executemany(
            'INSERT INTO TASK (PROJ_ID, TASK_ID, CLNDR_ID) VALUES (?, ?, ?)',
            [
                (26432, 1, 100),
                (26432, 2, 100),
                (99999, 3, 100),
            ],
        )
        cur.executemany(
            '''
            INSERT INTO TASKRSRC (
                PROJ_ID, TASK_ID, RSRC_TYPE, TARGET_QTY, TARGET_START_DATE, TARGET_END_DATE,
                ACT_REG_QTY, ACT_OT_QTY, ACT_START_DATE, ACT_END_DATE
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            [
                (26432, 1, 'RT_Labor', 80.0, '2026-02-16 08:00:00', '2026-02-20 18:00:00', 0.0, 0.0, None, None),
                (26432, 2, 'RT_Mat', 999.0, '2026-02-16 08:00:00', '2026-02-20 18:00:00', 0.0, 0.0, None, None),
                (99999, 3, 'RT_Labor', 500.0, '2026-02-16 08:00:00', '2026-02-20 18:00:00', 0.0, 0.0, None, None),
            ],
        )
        con.commit()
    finally:
        con.close()


def test_logic_uses_taskrsrc_rt_labor_for_pv_bac(tmp_path):
    db_path = tmp_path / 'pv_engine_fake.db'
    _build_fake_db(db_path)

    args = SimpleNamespace(
        mode='logic',
        cutoff='2026-02-20',
        base_xer=None,
        upd_xer=None,
        db=str(db_path),
        proj_id=26432,
    )

    payload = pv_engine.load(args)
    result = pv_engine.compute(payload)

    assert payload['base_source'] == 'db'
    assert len(payload['base_taskrsrc_rows']) == 1
    assert 100 in payload['calendars']
    assert result['mode'] == 'logic'
    assert result['stub'] is False
    assert result['bac'] == 80.0
    assert result['rows'][0]['week'] == 'W08'
    assert result['rows'][0]['pv_week'] == 80.0
    assert 'DB SQLite primaria' in result['note']


def test_a1060_reference_uses_hour_weight_not_flat_days():
    calendar = {
        'weekday_windows': {
            4: [(pv_engine.parse_clock('08:00'), pv_engine.parse_clock('13:00'))],  # viernes 5h
            0: [
                (pv_engine.parse_clock('08:00'), pv_engine.parse_clock('13:00')),
                (pv_engine.parse_clock('14:00'), pv_engine.parse_clock('19:00')),
            ],  # lunes 10h
            1: [(pv_engine.parse_clock('08:00'), pv_engine.parse_clock('13:00'))],  # martes 5h
        },
        'exceptions': set(),
    }

    start_dt = pv_engine.safe_dt('2026-09-11 08:00:00')  # viernes
    end_dt = pv_engine.safe_dt('2026-09-15 13:00:00')    # martes media jornada
    qty = 216.0

    by_day = {}
    day = start_dt.date()
    while day <= end_dt.date():
        hours = 0.0
        for win_start, win_end in calendar['weekday_windows'].get(day.weekday(), []):
            hours += pv_engine._overlap_hours(
                start_dt,
                end_dt,
                pv_engine.combine_dt(day, win_start),
                pv_engine.combine_dt(day, win_end),
            )
        if hours > 0:
            by_day[day] = hours
        day += timedelta(days=1)

    total_hours = sum(by_day.values())
    distributed = {day: qty * hours / total_hours for day, hours in by_day.items()}

    assert round(distributed[pv_engine.safe_dt('2026-09-11 08:00:00').date()], 4) == 54.0
    assert round(distributed[pv_engine.safe_dt('2026-09-14 08:00:00').date()], 4) == 108.0
    assert round(distributed[pv_engine.safe_dt('2026-09-15 08:00:00').date()], 4) == 54.0

    flat = qty / 3.0
    assert round(flat, 4) == 72.0
    assert round(distributed[pv_engine.safe_dt('2026-09-14 08:00:00').date()], 4) != round(flat, 4)

    bucket = {}
    pv_engine.spread_calendar(start_dt, end_dt, qty, calendar, bucket)
    assert round(bucket[pv_engine.safe_dt('2026-09-07 08:00:00').date()], 4) == 54.0
    assert round(bucket[pv_engine.safe_dt('2026-09-14 08:00:00').date()], 4) == 162.0
