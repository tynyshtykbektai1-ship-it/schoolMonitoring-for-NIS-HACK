# schoolMonitoring-for-NIS-HACK

## Quick Start (Teacher + Student)

Ниже запуск в формате "2 роли":
- учитель: сервер и (опционально) dashboard
- ученик: webcam monitor, отправляет нарушения на сервер учителя

## 1. Teacher Machine

Запуск:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_teacher.ps1 -WithDashboard
```

По умолчанию сервер стартует на `0.0.0.0:8000`.

Открыть интерфейс учителя:

```text
http://127.0.0.1:8000/
```

Если нужен другой порт:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_teacher.ps1 -Port 8010 -WithDashboard
```

## 2. Student Machine

Запуск ученика (пример, где IP учителя `192.168.1.15`):

```powershell
powershell -ExecutionPolicy Bypass -File .\start_student.ps1 -StudentId student_01 -ServerUrl http://192.168.1.15:8000 -EnablePhoneDetection
```

Без YOLO:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_student.ps1 -StudentId student_01 -ServerUrl http://192.168.1.15:8000
```

## 3. Network Notes

- Teacher server должен быть запущен с `--host 0.0.0.0` (в `start_teacher.ps1` это уже так).
- Student использует `ServerUrl` с IP учителя в локальной сети.
- При необходимости открой порт `8000` в Windows Firewall на машине учителя.

## 4. Scripts

- `start_teacher.ps1`: устанавливает `backend/requirements.txt`, запускает сервер, опционально dashboard.
- `start_student.ps1`: устанавливает `backend/requirements_webcam.txt`, запускает `backend/webcam_monitor.py`.
- `start_demo.ps1`: all-in-one запуск на одной машине (локальное демо).
