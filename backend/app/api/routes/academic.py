from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from pydantic import BaseModel, Field

from app.api.deps import require_teacher
from app.schemas.response import ApiResponse, ok
from app.services import academic as academic_service


router = APIRouter(prefix="/academic", tags=["academic"])


class CourseRequest(BaseModel):
    name: str = Field(min_length=1)
    teacher_name: str | None = None


class ClassRequest(BaseModel):
    name: str = Field(min_length=1)


class UpdateClassRequest(BaseModel):
    name: str = Field(min_length=1)


class CourseClassRequest(BaseModel):
    course_id: int
    class_id: int


class SessionRequest(BaseModel):
    course_id: int
    class_ids: list[int]
    title: str = Field(min_length=1)
    session_no: int = Field(gt=0)
    start_time: str | None = None
    end_time: str | None = None
    is_makeup: bool = False
    schedule_note: str | None = None


class ImportMappingRequest(BaseModel):
    mapping: dict[str, str]


class ConfirmImportRequest(BaseModel):
    class_id: int
    mapping: dict[str, str]
    import_valid_only: bool = True
    duplicate_strategy: str = "merge"


class StudentActiveRequest(BaseModel):
    is_active: bool


@router.get("/courses", response_model=ApiResponse[list[dict[str, object]]])
def courses(_teacher: dict[str, object] = Depends(require_teacher)) -> ApiResponse[list[dict[str, object]]]:
    return ok(academic_service.list_courses())


@router.post("/courses", response_model=ApiResponse[dict[str, object]])
def create_course(
    payload: CourseRequest,
    teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    teacher_name = payload.teacher_name or str(teacher.get("name") or "教师")
    return ok(academic_service.create_course(payload.name, int(teacher["id"]), teacher_name), message="课程已创建")


@router.get("/classes", response_model=ApiResponse[list[dict[str, object]]])
def classes(
    course_id: int | None = None,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[list[dict[str, object]]]:
    return ok(academic_service.list_classes(course_id))


@router.post("/classes", response_model=ApiResponse[dict[str, object]])
def create_class(
    payload: ClassRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(academic_service.create_class(payload.name), message="班级已创建")


@router.put("/classes/{class_id}", response_model=ApiResponse[dict[str, object]])
def update_class(
    class_id: int,
    payload: UpdateClassRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(academic_service.update_class(class_id, payload.name), message="班级已重命名")


@router.post("/course-classes", response_model=ApiResponse[dict[str, object]])
def link_course_class(
    payload: CourseClassRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(academic_service.link_course_class(payload.course_id, payload.class_id), message="课程班级已关联")


@router.get("/sessions", response_model=ApiResponse[list[dict[str, object]]])
def sessions(
    course_id: int | None = None,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[list[dict[str, object]]]:
    return ok(academic_service.list_sessions(course_id))


@router.post("/sessions", response_model=ApiResponse[dict[str, object]])
def create_session(
    payload: SessionRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(academic_service.create_session(payload.model_dump()), message="课堂已创建")


@router.get("/students", response_model=ApiResponse[list[dict[str, object]]])
def students(
    course_id: int | None = None,
    class_id: int | None = None,
    include_inactive: bool = False,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[list[dict[str, object]]]:
    return ok(academic_service.list_students(course_id, class_id, include_inactive))


@router.put("/students/{student_pk}/active", response_model=ApiResponse[dict[str, object]])
def set_student_active(
    student_pk: int,
    payload: StudentActiveRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(
        academic_service.set_student_active(student_pk, payload.is_active),
        message="学生状态已更新",
    )


@router.post("/imports/excel", response_model=ApiResponse[dict[str, object]])
async def upload_excel(
    file: UploadFile = File(...),
    sheet_name: str | None = Form(None),
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    content = await file.read()
    return ok(
        academic_service.parse_excel_upload(
            file.filename or "students.xlsx", len(content), content, sheet_name
        ),
        message="Excel 已解析",
    )


@router.post("/imports/{job_id}/preview", response_model=ApiResponse[dict[str, object]])
def preview_import(
    job_id: int,
    payload: ImportMappingRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(academic_service.preview_import(job_id, payload.mapping))


@router.post("/imports/{job_id}/mapping-suggestion", response_model=ApiResponse[dict[str, object]])
def suggest_import_mapping(
    job_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(academic_service.suggest_import_mapping(job_id))


@router.get("/imports/{job_id}/errors.csv")
def export_import_errors(
    job_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> Response:
    exported = academic_service.export_import_errors(job_id)
    return Response(
        content=exported["content"],
        media_type=exported["content_type"],
        headers={"Content-Disposition": f"attachment; filename={exported['file_name']}"},
    )


@router.post("/imports/{job_id}/confirm", response_model=ApiResponse[dict[str, object]])
def confirm_import(
    job_id: int,
    payload: ConfirmImportRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(
        academic_service.confirm_import(
            job_id,
            payload.class_id,
            payload.mapping,
            payload.import_valid_only,
            payload.duplicate_strategy,
        ),
        message="学生名单已导入",
    )
