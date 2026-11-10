from pydantic import BaseModel,Field,StringConstraints,ConfigDict
from typing import Annotated,Any
NonBlank=Annotated[str,StringConstraints(strip_whitespace=True,min_length=2)]
Sentence=Annotated[str,StringConstraints(strip_whitespace=True,min_length=5)]
class WeatherArgs(BaseModel):
    city:NonBlank=Field(description="城市名，例如：上海")
    model_config=ConfigDict(extra="forbid")

class WeatherAnswer(BaseModel):
    city:NonBlank=Field(description="城市名，例如：上海")
    temp:float=Field(description="温度，摄氏度")
    condition:NonBlank=Field(description="天气状况，例如：多云，东南分三级")
    model_config=ConfigDict(extra="forbid")


class SearchArgs(BaseModel):
    query:NonBlank=Field(description="搜索问题")
    model_config=ConfigDict(extra="forbid")

class SearchAnswer(BaseModel):
    query:NonBlank=Field(description="搜索关键词")
    result:str=Field(description="搜索结果，可能是直接答案，知识图谱或者网页搜索摘要")
    model_config=ConfigDict(extra="forbid")

class Step(BaseModel):
    thought:Sentence=Field(description="本轮推理过程")
    action:NonBlank=Field(description="要调用的工具名，任务完成时填Finish")
    action_input:dict[str,Any]=Field(
        default_factory=dict,
        description='工具参数，例如 {"city": "北京"}；Action=Final Answer 时放 summary/sources/confidence',
    )
    model_config=ConfigDict(extra='forbid')

class FinalAnswer(BaseModel):
    summary:Sentence=Field(description="用一道两句话给出可执行的建议")
    sources:list[str]=Field(default_factory=list,description="结论依据，填实际调用过的工具名，例如get_weather,")
    confidence:float=Field(ge=0,le=1,description="置信度，0到1之间的数字，例如0.5")
    