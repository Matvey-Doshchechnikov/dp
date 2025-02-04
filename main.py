from fastapi import FastAPI, HTTPException
import os
import yaml
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI()
COURSES_DIR = "courses"
CREDENTIALS_FILE = "credentials.json"  # Файл с учетными данными Google API


@app.get("/courses")
def get_courses():
    courses = []
    for index, filename in enumerate(sorted(os.listdir(COURSES_DIR)), start=1):
        file_path = os.path.join(COURSES_DIR, filename)
        if filename.endswith(".yaml") and os.path.isfile(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
                course_info = data.get("course", {})
                courses.append({
                    "id": str(index),
                    "name": course_info.get("name", "Unknown"),
                    "semester": course_info.get("semester", "Unknown"),
                })
    return courses


@app.get("/courses/{course_id}")
def get_course(course_id: str):
    files = sorted([f for f in os.listdir(COURSES_DIR) if f.endswith(".yaml")])
    try:
        filename = files[int(course_id) - 1]
    except (IndexError, ValueError):
        raise HTTPException(status_code=404, detail="Course not found")

    file_path = os.path.join(COURSES_DIR, filename)
    with open(file_path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
        course_info = data.get("course", {})
        return {
            "id": course_id,
            "config": filename,
            "name": course_info.get("name", "Unknown"),
            "semester": course_info.get("semester", "Unknown"),
            "email": course_info.get("email", "Unknown"),
            "github-organization": course_info.get("github", {}).get("organization", "Unknown"),
            "google-spreadsheet": course_info.get("google", {}).get("spreadsheet", "Unknown"),
        }


@app.get("/courses/{course_id}/groups")
def get_course_groups(course_id: str):
    files = sorted([f for f in os.listdir(COURSES_DIR) if f.endswith(".yaml")])
    try:
        filename = files[int(course_id) - 1]
    except (IndexError, ValueError):
        raise HTTPException(status_code=404, detail="Course not found")

    file_path = os.path.join(COURSES_DIR, filename)
    with open(file_path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
        course_info = data.get("course", {})
        spreadsheet_id = course_info.get("google", {}).get("spreadsheet")
        info_sheet = course_info.get("google", {}).get("info-sheet")

    if not spreadsheet_id:
        raise HTTPException(status_code=400, detail="Spreadsheet ID not found in course config")

    # Авторизация в Google Sheets API
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)

    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        sheet_names = [sheet.title for sheet in spreadsheet.worksheets() if sheet.title != info_sheet]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sheets: {str(e)}")

    return sheet_names


@app.get("/courses/{course_id}/groups/{group_id}/labs")
def get_course_labs(course_id: str, group_id: str):
    files = sorted([f for f in os.listdir(COURSES_DIR) if f.endswith(".yaml")])
    try:
        filename = files[int(course_id) - 1]
    except (IndexError, ValueError):
        raise HTTPException(status_code=404, detail="Course not found")

    file_path = os.path.join(COURSES_DIR, filename)
    with open(file_path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
        course_info = data.get("course", {})
        spreadsheet_id = course_info.get("google", {}).get("spreadsheet")
        labs = [lab["short-name"] for lab in course_info.get("labs", {}).values() if "short-name" in lab]

    if not spreadsheet_id or not labs:
        raise HTTPException(status_code=400, detail="Missing spreadsheet ID or labs in config")

    # Авторизация в Google Sheets API
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)

    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        sheet = spreadsheet.worksheet(group_id)
        headers = sheet.row_values(1)  # Получаем названия столбцов
    except Exception:
        raise HTTPException(status_code=404, detail="Group not found in spreadsheet")

    available_labs = [lab for lab in labs if lab in headers]
    return available_labs
