"""
Job Matcher - Scores job listings against resume profile.
"""

import logging
import re
from rapidfuzz import fuzz

from .resume_parser import ResumeProfile

logger = logging.getLogger(__name__)


class JobMatcher:
    def __init__(self, profile: ResumeProfile, config: dict):
        self.profile = profile
        self.config = config
        self.min_score = config.get("matching", {}).get("min_score", 60)
        self.min_skills_match = config.get("matching", {}).get("min_skills_match", 3)
        self.exclude_companies = [
            c.lower() for c in config.get("filters", {}).get("exclude_companies", [])
        ]
        self.exclude_titles = [
            t.lower() for t in config.get("filters", {}).get("exclude_titles", [])
        ]

        # Combine resume skills + extra configured skills
        extra = config.get("extra_skills", [])
        self.all_skills = set(s.lower() for s in self.profile.skills)
        self.all_skills.update(s.lower() for s in extra)

    def score_job(self, job: dict) -> float:
        """
        Score a job listing from 0-100.
        Factors: skill match, title relevance, experience fit.
        """
        scores = {}

        # 1. Skill match (50% weight)
        scores["skills"] = self._skill_match_score(job)

        # 2. Title relevance (30% weight)
        scores["title"] = self._title_match_score(job)

        # 3. Experience fit (20% weight)
        scores["experience"] = self._experience_match_score(job)

        total = (
            scores["skills"] * 0.50
            + scores["title"] * 0.30
            + scores["experience"] * 0.20
        )

        logger.debug(
            f"Job: {job.get('title', '')} @ {job.get('company', '')} | "
            f"Skills: {scores['skills']:.0f} | Title: {scores['title']:.0f} | "
            f"Exp: {scores['experience']:.0f} | Total: {total:.0f}"
        )

        return round(total, 2)

    def _skill_match_score(self, job: dict) -> float:
        """Score based on how many required skills match."""
        job_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
        job_skills = job.get("skills_required", [])

        if isinstance(job_skills, str):
            job_skills = [s.strip() for s in job_skills.split(",") if s.strip()]

        # Extract skills from job text
        job_skill_set = set(s.lower() for s in job_skills)
        for skill in self.all_skills:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, job_text):
                job_skill_set.add(skill)

        if not job_skill_set:
            return 50.0  # No skills listed, give neutral score

        # Count matches
        matched = self.all_skills.intersection(job_skill_set)
        match_ratio = len(matched) / max(len(job_skill_set), 1)

        return min(match_ratio * 100, 100)

    def _title_match_score(self, job: dict) -> float:
        """Score based on job title similarity to desired titles."""
        job_title = job.get("title", "").lower()

        if not job_title:
            return 0.0

        search_titles = self.config.get("search", {}).get("titles", [])
        resume_titles = self.profile.job_titles

        all_desired = [t.lower() for t in search_titles + resume_titles]

        if not all_desired:
            return 50.0

        best_score = 0
        for desired in all_desired:
            score = fuzz.token_sort_ratio(job_title, desired)
            best_score = max(best_score, score)

        return best_score

    def _experience_match_score(self, job: dict) -> float:
        """Score based on experience level fit."""
        my_exp = self.profile.experience_years
        if my_exp == 0:
            my_exp = self.config.get("search", {}).get("experience_years", 0)

        if my_exp == 0:
            return 50.0  # Unknown, give neutral

        # Try to extract required experience from job
        job_text = f"{job.get('title', '')} {job.get('description', '')} {job.get('experience', '')}"
        exp_patterns = [
            r"(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)",
            r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)",
            r"minimum\s*(\d+)\s*(?:years?|yrs?)",
        ]

        min_exp = None
        max_exp = None

        for pattern in exp_patterns:
            match = re.search(pattern, job_text.lower())
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    min_exp = float(groups[0])
                    max_exp = float(groups[1])
                elif len(groups) == 1:
                    min_exp = float(groups[0])
                    max_exp = min_exp + 3
                break

        if min_exp is None:
            return 60.0  # No requirement mentioned

        # Perfect fit: experience is within range
        if min_exp <= my_exp <= (max_exp or min_exp + 3):
            return 100.0
        # Slightly over-qualified (1-2 years over)
        elif my_exp > (max_exp or min_exp + 3):
            diff = my_exp - (max_exp or min_exp + 3)
            return max(100 - diff * 15, 20)
        # Under-qualified
        else:
            diff = min_exp - my_exp
            # If within 1 year, still decent match
            if diff <= 1:
                return 75.0
            return max(100 - diff * 25, 10)

    def should_apply(self, job: dict) -> tuple:
        """
        Determine if we should auto-apply to this job.
        Returns (should_apply: bool, score: float, reason: str)
        """
        # Check exclusion filters first
        company = job.get("company", "").lower()
        title = job.get("title", "").lower()

        for excluded in self.exclude_companies:
            if excluded in company:
                return False, 0, f"Excluded company: {company}"

        for excluded in self.exclude_titles:
            if excluded in title:
                return False, 0, f"Excluded title keyword: {excluded}"

        # Score the job
        score = self.score_job(job)

        if score >= self.min_score:
            return True, score, f"Score {score:.0f} >= threshold {self.min_score}"
        else:
            return False, score, f"Score {score:.0f} < threshold {self.min_score}"
