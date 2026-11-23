from pydantic import BaseModel, Field


class SubmitPrunedProfile(BaseModel):
    pruned_profile: str = Field(
        description="Clean, pruned Markdown text containing strictly role-relevant experience, gap-filling projects, and essential skills."
    )