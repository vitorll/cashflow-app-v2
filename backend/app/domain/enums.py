import enum


class Phase(str, enum.Enum):
    p1 = "p1"
    p2 = "p2"
    p3 = "p3"
    p4 = "p4"
    p5 = "p5"
    total = "total"


class SectionType(str, enum.Enum):
    revenue = "revenue"
    direct_costs = "direct_costs"
    overheads = "overheads"
    capex = "capex"
    contingency = "contingency"


class SeriesType(str, enum.Enum):
    cumulative = "cumulative"
    periodic = "periodic"


class ImportStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class VersionType(str, enum.Enum):
    budget = "budget"
    current = "current"
    forecast = "forecast"


class SourceType(str, enum.Enum):
    excel = "excel"
    manual = "manual"
    api = "api"


PHASES = [Phase.p1, Phase.p2, Phase.p3, Phase.p4, Phase.p5]
