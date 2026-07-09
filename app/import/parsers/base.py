from abc import ABC, abstractmethod


class BaseParser(ABC):

    @abstractmethod
    def parse(self, raw_data) -> dict:
        pass

    def _empty_result(self) -> dict:
        return {
            "personal_info": {},
            "summary": "",
            "experience": [],
            "education": [],
            "projects": [],
            "skills": [],
            "certificates": [],
            "achievements": [],
            "languages": [],
            "publications": [],
        }
