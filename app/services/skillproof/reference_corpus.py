"""Curated reference corpus registry of legitimate canonical templates and documentation examples.

Contains official quickstarts, starter templates, and canonical boilerplate with verifiable provenance.
Used exclusively for similarity comparisons against legitimate sources; never fabricates similarity.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReferenceSource:
    """A legitimate reference code snippet with source provenance."""

    reference_id: str
    name: str
    provenance: str
    license: str
    canonical_url: str
    skill: str
    language: str
    code: str


# Canonical reference snippets from official documentation and canonical open-source templates
CANONICAL_REFERENCES: list[ReferenceSource] = [
    ReferenceSource(
        reference_id="fastapi_quickstart_main",
        name="FastAPI Tutorial - First Steps",
        provenance="Official FastAPI Documentation (Tiangolo)",
        license="MIT License",
        canonical_url="https://fastapi.tiangolo.com/tutorial/first-steps/",
        skill="FastAPI",
        language="Python",
        code="""from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
""",
    ),
    ReferenceSource(
        reference_id="fastapi_crud_router",
        name="FastAPI Bigger Applications - APIRouter",
        provenance="Official FastAPI Documentation",
        license="MIT License",
        canonical_url="https://fastapi.tiangolo.com/tutorial/bigger-applications/",
        skill="FastAPI",
        language="Python",
        code="""from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/items", tags=["items"])

class Item(BaseModel):
    id: str
    title: str
    description: str | None = None

@router.get("/", response_model=list[Item])
async def read_items():
    return []

@router.get("/{item_id}", response_model=Item)
async def read_item(item_id: str):
    return {"id": item_id, "title": "Sample Item"}
""",
    ),
    ReferenceSource(
        reference_id="sqlalchemy_declarative_base",
        name="SQLAlchemy 2.0 Declarative Base & Session",
        provenance="Official SQLAlchemy Documentation",
        license="MIT License",
        canonical_url="https://docs.sqlalchemy.org/en/20/orm/quickstart.html",
        skill="SQLAlchemy",
        language="Python",
        code="""from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    fullname: Mapped[str | None]
""",
    ),
    ReferenceSource(
        reference_id="pydantic_v2_basemodel",
        name="Pydantic V2 BaseModel Definition",
        provenance="Official Pydantic Documentation",
        license="MIT License",
        canonical_url="https://docs.pydantic.dev/latest/concepts/models/",
        skill="Pydantic",
        language="Python",
        code="""from datetime import datetime
from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    id: int
    name: str = "John Doe"
    signup_ts: datetime | None = None
    tastes: dict[str, int] = Field(default_factory=dict)
""",
    ),
    ReferenceSource(
        reference_id="flask_basic_app",
        name="Flask Quickstart Application",
        provenance="Pallets Projects Official Flask Documentation",
        license="BSD-3-Clause",
        canonical_url="https://flask.palletsprojects.com/en/latest/quickstart/",
        skill="Flask",
        language="Python",
        code="""from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello, World!"

@app.route("/api/data", methods=["POST"])
def post_data():
    data = request.get_json()
    return jsonify(data), 201
""",
    ),
    ReferenceSource(
        reference_id="django_basic_model_view",
        name="Django Tutorial - Models & Views",
        provenance="Official Django Documentation",
        license="BSD-3-Clause",
        canonical_url="https://docs.djangoproject.com/en/5.0/intro/tutorial01/",
        skill="Django",
        language="Python",
        code="""from django.db import models
from django.http import HttpResponse

class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField("date published")

    def __str__(self):
        return self.question_text

def index(request):
    return HttpResponse("Hello, world. You're at the polls index.")
""",
    ),
    ReferenceSource(
        reference_id="react_quickstart_component",
        name="React Official Quickstart Functional Component",
        provenance="Official React Documentation (Meta Open Source)",
        license="MIT License",
        canonical_url="https://react.dev/learn",
        skill="React",
        language="JavaScript",
        code="""import React, { useState, useEffect } from 'react';

export default function CounterButton() {
  const [count, setCount] = useState(0);

  function handleClick() {
    setCount(count + 1);
  }

  return (
    <button onClick={handleClick}>
      Clicked {count} times
    </button>
  );
}
""",
    ),
    ReferenceSource(
        reference_id="express_hello_world",
        name="Express.js Hello World Starter",
        provenance="Express.js Official Guide (OpenJS Foundation)",
        license="CC-BY-SA 3.0 / MIT",
        canonical_url="https://expressjs.com/en/starter/hello-world.html",
        skill="Express.js",
        language="JavaScript",
        code="""const express = require('express');
const app = express();
const port = 3000;

app.use(express.json());

app.get('/', (req, res) => {
  res.send('Hello World!');
});

app.listen(port, () => {
  console.log(`Example app listening on port ${port}`);
});
""",
    ),
    ReferenceSource(
        reference_id="dockerfile_python_standard",
        name="Standard Python Container Dockerfile",
        provenance="Docker Official Images - Python Library",
        license="Apache-2.0",
        canonical_url="https://hub.docker.com/_/python",
        skill="Docker",
        language="Dockerfile",
        code="""FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
""",
    ),
    ReferenceSource(
        reference_id="github_actions_ci_workflow",
        name="GitHub Actions Python Starter Workflow",
        provenance="GitHub Starter Workflows",
        license="MIT License",
        canonical_url="https://github.com/actions/starter-workflows",
        skill="GitHub Actions",
        language="YAML",
        code="""name: Python package

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Test with pytest
      run: |
        pytest
""",
    ),
]


class ReferenceCorpusRegistry:
    """Registry managing available reference corpora."""

    def __init__(self, references: list[ReferenceSource] | None = None) -> None:
        self._references = list(references or CANONICAL_REFERENCES)

    def get_references_for_skill(self, skill_name: str) -> list[ReferenceSource]:
        """Retrieve references matching a specific skill (case-insensitive)."""
        target = skill_name.strip().lower()
        return [r for r in self._references if r.skill.lower() == target]

    def get_references_for_language(self, language: str) -> list[ReferenceSource]:
        """Retrieve references matching a programming language."""
        target = language.strip().lower()
        return [r for r in self._references if r.language.lower() == target]

    def has_references_for_skill(self, skill_name: str) -> bool:
        """Check if any reference sources exist for the skill."""
        return len(self.get_references_for_skill(skill_name)) > 0

    def list_all(self) -> list[ReferenceSource]:
        """Return all registered reference sources."""
        return list(self._references)


reference_registry = ReferenceCorpusRegistry()
