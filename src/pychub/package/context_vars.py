from contextvars import ContextVar

# Hold the active BuildPlan during the build lifecycle
current_build_plan: ContextVar["BuildPlan"] = ContextVar("current_build_plan")
