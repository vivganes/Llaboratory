from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.models import Tool, ToolVersion
from app.schemas import ToolCreate, ToolOut, ToolUpdate, ToolVersionNewIn, ToolVersionOut

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolOut])
def list_tools(db: Session = Depends(get_db)):
    return db.query(Tool).order_by(Tool.created_at.desc()).all()


@router.post("", response_model=ToolOut, status_code=201)
def create_tool(body: ToolCreate, db: Session = Depends(get_db)):
    tool = Tool(
        name=body.name,
        description=body.description,
        tags=json.dumps(body.tags),
    )
    db.add(tool)
    db.flush()

    tv = ToolVersion(
        tool_id=tool.id,
        version_number=1,
        display_name=body.version.display_name,
        model_facing_description=body.version.model_facing_description,
        parameter_schema=json.dumps(body.version.parameter_schema),
        response_mode=body.version.response_mode,
        static_response=json.dumps(body.version.static_response),
        dynamic_code=body.version.dynamic_code,
        dynamic_approved=1,
    )
    db.add(tv)
    db.commit()
    db.refresh(tool)
    return tool


@router.get("/{tool_id}", response_model=ToolOut)
def get_tool(tool_id: str, db: Session = Depends(get_db)):
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(404, "Tool not found")
    return tool


@router.patch("/{tool_id}", response_model=ToolOut)
def update_tool_meta(tool_id: str, body: ToolUpdate, db: Session = Depends(get_db)):
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(404, "Tool not found")
    if body.name is not None:
        tool.name = body.name
    if body.description is not None:
        tool.description = body.description
    if body.tags is not None:
        tool.tags = json.dumps(body.tags)
    db.commit()
    db.refresh(tool)
    return tool


@router.post("/{tool_id}/versions", response_model=ToolVersionOut, status_code=201)
def add_tool_version(tool_id: str, body: ToolVersionNewIn, db: Session = Depends(get_db)):
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(404, "Tool not found")

    next_version = max((tv.version_number for tv in tool.versions), default=0) + 1
    tv = ToolVersion(
        tool_id=tool_id,
        version_number=next_version,
        display_name=body.display_name,
        model_facing_description=body.model_facing_description,
        parameter_schema=json.dumps(body.parameter_schema),
        response_mode=body.response_mode,
        static_response=json.dumps(body.static_response),
        dynamic_code=body.dynamic_code,
        dynamic_approved=1,
    )
    db.add(tv)
    db.commit()
    db.refresh(tv)
    return tv


@router.delete("/{tool_id}", status_code=204)
def delete_tool(tool_id: str, db: Session = Depends(get_db)):
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(404, "Tool not found")
    db.delete(tool)
    db.commit()
