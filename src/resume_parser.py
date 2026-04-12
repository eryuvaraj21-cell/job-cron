"""
Resume Parser - Extracts skills, experience, education from PDF/DOCX resumes.
"""

import os
import re
from pathlib import Path
from dataclasses import dataclass, field

from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document


@dataclass
class ResumeProfile:
    name: str = ""
    email: str = ""
    phone: str = ""
    skills: list = field(default_factory=list)
    experience_years: float = 0.0
    job_titles: list = field(default_factory=list)
    education: list = field(default_factory=list)
    raw_text: str = ""

    def to_dict(self):
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "skills": self.skills,
            "experience_years": self.experience_years,
            "job_titles": self.job_titles,
            "education": self.education,
        }


# Comprehensive skills database organized by category
SKILLS_DB = {
    # Programming Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go",
    "golang", "rust", "swift", "kotlin", "scala", "php", "perl", "r",
    "matlab", "dart", "lua", "shell", "bash", "powershell", "sql", "nosql",
    "html", "css", "sass", "less",

    # Frontend Frameworks
    "react", "reactjs", "react.js", "angular", "angularjs", "vue", "vuejs",
    "vue.js", "svelte", "next.js", "nextjs", "nuxt.js", "nuxtjs", "gatsby",
    "ember", "backbone", "jquery", "bootstrap", "tailwind", "tailwindcss",
    "material ui", "chakra ui", "ant design", "redux", "mobx", "zustand",

    # Backend Frameworks
    "node.js", "nodejs", "express", "express.js", "fastapi", "django",
    "flask", "spring", "spring boot", "springboot", ".net", "asp.net",
    "rails", "ruby on rails", "laravel", "gin", "fiber", "actix",
    "nestjs", "nest.js", "koa", "hapi", "fastify",

    # Databases
    "mysql", "postgresql", "postgres", "mongodb", "redis", "elasticsearch",
    "cassandra", "dynamodb", "sqlite", "oracle", "sql server", "mariadb",
    "couchdb", "neo4j", "influxdb", "firebase", "supabase", "cockroachdb",

    # Cloud & DevOps
    "aws", "amazon web services", "azure", "gcp", "google cloud",
    "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins",
    "ci/cd", "github actions", "gitlab ci", "circleci", "travis ci",
    "helm", "prometheus", "grafana", "nginx", "apache", "cloudflare",
    "heroku", "vercel", "netlify", "digitalocean", "linux", "ubuntu",

    # Data & ML
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "tensorflow", "pytorch", "keras", "scikit-learn",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "jupyter",
    "spark", "hadoop", "airflow", "kafka", "rabbitmq", "celery",
    "data science", "data engineering", "etl", "data pipeline",
    "power bi", "tableau", "looker",

    # Tools & Practices
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "agile", "scrum", "kanban", "rest", "restful", "graphql", "grpc",
    "microservices", "monolith", "serverless", "api", "oauth", "jwt",
    "websocket", "tcp/ip", "http", "dns",

    # Mobile
    "android", "ios", "react native", "flutter", "xamarin", "ionic",
    "swift ui", "swiftui", "jetpack compose",

    # Testing
    "jest", "mocha", "pytest", "junit", "selenium", "cypress",
    "playwright", "testing", "unit testing", "integration testing",
    "tdd", "bdd",

    # Other
    "blockchain", "solidity", "web3", "figma", "adobe",
    "sap", "salesforce", "servicenow", "sharepoint",
}

# Common job title patterns
JOB_TITLE_PATTERNS = [
    r"software\s+engineer",
    r"software\s+developer",
    r"full\s*[-\s]?stack\s+developer",
    r"front\s*[-\s]?end\s+developer",
    r"back\s*[-\s]?end\s+developer",
    r"web\s+developer",
    r"mobile\s+developer",
    r"data\s+scientist",
    r"data\s+engineer",
    r"data\s+analyst",
    r"machine\s+learning\s+engineer",
    r"ml\s+engineer",
    r"devops\s+engineer",
    r"cloud\s+engineer",
    r"site\s+reliability\s+engineer",
    r"sre",
    r"product\s+manager",
    r"project\s+manager",
    r"technical\s+lead",
    r"tech\s+lead",
    r"team\s+lead",
    r"architect",
    r"qa\s+engineer",
    r"test\s+engineer",
    r"ui/ux\s+designer",
    r"system\s+administrator",
    r"database\s+administrator",
    r"network\s+engineer",
    r"security\s+engineer",
    r"business\s+analyst",
]

EDUCATION_PATTERNS = [
    r"b\.?tech",
    r"m\.?tech",
    r"b\.?e\.?",
    r"m\.?e\.?",
    r"b\.?sc",
    r"m\.?sc",
    r"b\.?c\.?a",
    r"m\.?c\.?a",
    r"mba",
    r"ph\.?d",
    r"bachelor",
    r"master",
    r"diploma",
    r"computer\s+science",
    r"information\s+technology",
    r"electrical\s+engineering",
    r"electronics",
    r"mechanical\s+engineering",
]


class ResumeParser:
    def __init__(self, resume_path: str):
        self.resume_path = Path(resume_path)
        if not self.resume_path.exists():
            raise FileNotFoundError(f"Resume not found: {resume_path}")

    def parse(self) -> ResumeProfile:
        """Parse resume and return structured profile."""
        raw_text = self._extract_text()
        profile = ResumeProfile(raw_text=raw_text)

        profile.email = self._extract_email(raw_text)
        profile.phone = self._extract_phone(raw_text)
        profile.name = self._extract_name(raw_text)
        profile.skills = self._extract_skills(raw_text)
        profile.experience_years = self._extract_experience_years(raw_text)
        profile.job_titles = self._extract_job_titles(raw_text)
        profile.education = self._extract_education(raw_text)

        return profile

    def _extract_text(self) -> str:
        """Extract text from PDF or DOCX."""
        ext = self.resume_path.suffix.lower()

        if ext == ".pdf":
            return extract_pdf_text(str(self.resume_path))
        elif ext in (".docx", ".doc"):
            doc = Document(str(self.resume_path))
            return "\n".join(para.text for para in doc.paragraphs)
        elif ext == ".txt":
            return self.resume_path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"Unsupported resume format: {ext}")

    def _extract_email(self, text: str) -> str:
        match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
        return match.group(0) if match else ""

    def _extract_phone(self, text: str) -> str:
        match = re.search(
            r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}", text
        )
        return match.group(0).strip() if match else ""

    def _extract_name(self, text: str) -> str:
        """Extract name - usually the first non-empty line of a resume."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if lines:
            first_line = lines[0]
            # Name is usually short and doesn't contain special chars
            if len(first_line) < 50 and not re.search(r"[@#$%^&*(){}[\]]", first_line):
                return first_line
        return ""

    def _extract_skills(self, text: str) -> list:
        """Extract skills by matching against skills database."""
        text_lower = text.lower()
        found_skills = set()

        for skill in SKILLS_DB:
            # Use word boundary matching to avoid partial matches
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, text_lower):
                found_skills.add(skill)

        # Normalize duplicates (e.g., "react.js" and "reactjs")
        normalized = set()
        seen_bases = set()
        for skill in sorted(found_skills, key=len, reverse=True):
            base = skill.replace(".", "").replace("-", "").replace(" ", "").lower()
            if base not in seen_bases:
                normalized.add(skill)
                seen_bases.add(base)

        return sorted(normalized)

    def _extract_experience_years(self, text: str) -> float:
        """Extract total years of experience."""
        # Pattern: "X years of experience" or "X+ years"
        patterns = [
            r"(\d+\.?\d*)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)",
            r"experience\s*(?:of)?\s*(\d+\.?\d*)\+?\s*(?:years?|yrs?)",
            r"(\d+\.?\d*)\+?\s*(?:years?|yrs?)\s*(?:in\s+(?:software|it|tech))",
        ]

        max_years = 0.0
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                years = float(match)
                if 0 < years < 50:  # Sanity check
                    max_years = max(max_years, years)

        # If no explicit mention, try to calculate from date ranges
        if max_years == 0:
            year_pattern = r"(20\d{2}|19\d{2})"
            years_found = [int(y) for y in re.findall(year_pattern, text)]
            if len(years_found) >= 2:
                max_years = max(years_found) - min(years_found)

        return max_years

    def _extract_job_titles(self, text: str) -> list:
        """Extract job titles mentioned in resume."""
        text_lower = text.lower()
        titles = []

        for pattern in JOB_TITLE_PATTERNS:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                title = match.strip().title()
                if title not in titles:
                    titles.append(title)

        return titles

    def _extract_education(self, text: str) -> list:
        """Extract education qualifications."""
        text_lower = text.lower()
        education = []

        for pattern in EDUCATION_PATTERNS:
            if re.search(r"\b" + pattern + r"\b", text_lower):
                match_text = re.search(r"\b" + pattern + r"\b", text_lower).group(0)
                education.append(match_text.upper() if len(match_text) <= 5 else match_text.title())

        return list(set(education))
