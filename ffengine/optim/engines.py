from ._models import OrderMatchingModel
from ffengine.data import MatchSet, Match, OrderSet
import abc

class Engine(abc.ABC):
    
    @abc.abstractmethod
    def get_orderset(self)->OrderSet:
        pass

    @abc.abstractmethod
    def preprocess(self):
        pass

    @abc.abstractmethod
    def run_matching(self):
        pass

    @abc.abstractmethod
    def get_matches(self) -> MatchSet:
        pass

class OMMEngine(Engine):
    pass