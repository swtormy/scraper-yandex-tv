from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, model_validator


class ProgramTypeModel(BaseModel):
    id: int | None = None
    name: str
    alias: str | None = None
    isFilm: bool
    isSerial: bool
    isForChildren: bool


class ChannelGenreModel(BaseModel):
    id: int | None = None
    name: str
    alias: str | None = None


class ProgramTypeInfoModel(BaseModel):
    id: int
    name: str
    alias: str | None = None
    isFilm: bool
    isSerial: bool
    isForChildren: bool


class ProgramModel(BaseModel):
    id: int
    title: str
    transliteratedTitle: str | None = None
    mainImageBaseUrl: str | None = None
    favourite: bool
    tags: List[Any] = []
    displayIfNoEvents: bool
    duplicateIds: List[int] = []
    url: str
    images: List[Any] = []
    onlines: List[Any] = []
    trailers: List[Any] = []
    type: ProgramTypeInfoModel


class EpisodeModel(BaseModel):
    id: int
    title: str


class EventModel(BaseModel):
    id: int
    channelId: int
    channelFamilyId: int
    live: bool
    episode: Optional[EpisodeModel]
    program: Optional[ProgramModel]
    start: str
    finish: str
    hasSubtitles: bool
    yacFamilyId: int
    title: str
    programTitle: str
    episodeTitle: str
    seasonTitle: str
    url: str
    hasDescription: bool
    hasReminder: bool
    hasReminderButton: bool
    startTime: str
    hasStarted: bool
    isNow: bool
    hasFinished: bool
    progress: int
    humanDate: str


class ChannelLogoSizeModel(BaseModel):
    src: str


class ChannelLogoModel(BaseModel):
    original: ChannelLogoSizeModel
    sizes: Dict[str, ChannelLogoSizeModel]
    originalSize: ChannelLogoSizeModel
    maxSize: ChannelLogoSizeModel


class ChannelModel(BaseModel):
    title: str
    familyTitle: str
    transliteratedFamilyTitle: Optional[str]
    logo: ChannelLogoModel
    synonyms: List[str] = []
    familyId: int
    id: int
    genres: List[Dict[str, Union[int, str]]]
    type: str
    url: str
    isFavorite: bool
    hasBroadcasting: bool
    broadcastingUrl: str
    hasBroadcastingPlayer: bool
    broadcastingPlayerUrl: str


class ScheduleItemModel(BaseModel):
    finish: str | None = None
    events: List[EventModel]
    channel: ChannelModel
    hasFinished: bool


class ScheduleMapModel(BaseModel):
    id: int
    limit: int
    offset: int
    channelIds: List[int]


class ProviderPackageModel(BaseModel):
    id: int
    title: str


class ProviderModel(BaseModel):
    id: int
    title: str
    packages: List[ProviderPackageModel] = []


class WatchableChannelsItemModel(BaseModel):
    enabled: bool
    channels: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    def split_enabled_and_channels(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        enabled_value = data.pop("enabled", False)
        return {
            "enabled": enabled_value,
            "channels": data,
        }


class WatchableChannelsModel(BaseModel):
    multiplexChannels: WatchableChannelsItemModel
    otherChannels: "WatchableChannelsModel"


class RecommendedOttBlockModel(BaseModel):
    title: str
    subtitle: str
    utmSource: str
    yaVideoMap: Dict[str, str]
    utmCampaign: str


class ScheduleResponseModel(BaseModel):
    isMain: bool
    isMy: bool
    isAll: bool
    selectedDate: str
    selectedPeriod: str
    selectedChannelGenre: str
    programTypes: List[ProgramTypeModel]
    channelGenres: List[ChannelGenreModel]
    selectedProgramTypes: List[Any]
    availableProgramTypes: List[str]
    schedules: List[ScheduleItemModel]
    scheduleMap: List[ScheduleMapModel]
    currentPage: int
    providers: List[ProviderModel]
    dndEnabled: bool
    totalPages: int
    favoriteChannelIds: List[Any]
    hasRecommendedEditorial: bool
    recommendedOttBlock: Optional[RecommendedOttBlockModel]
    watchableChannels: WatchableChannelsModel


class RootModel(BaseModel):
    schedule: ScheduleResponseModel


class ChunkModel(BaseModel):
    currentPage: int
    schedules: List[ScheduleItemModel]
