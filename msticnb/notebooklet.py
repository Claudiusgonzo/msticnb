# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""Notebooklet base classes."""
from abc import ABC, abstractmethod
import re
from typing import Optional, Any, Iterable, List, Set, Tuple


import attr
from attr import Factory
import pandas as pd
import tqdm

from msticpy.data import QueryProvider

from .data_providers import DataProviders
from .common import TimeSpan, NotebookletException

from ._version import VERSION

__version__ = VERSION
__author__ = "Ian Hellen"


@attr.s(auto_attribs=True)
class NotebookletResult:
    """Base result class."""

    description: str = "Default Result"


@attr.s(auto_attribs=True)
class NBMetaData:
    """Notebooklet metadata class."""

    name: str
    description: str
    options: List[str] = Factory(list)
    default_options: List[str] = Factory(list)
    entity_types: List[str] = Factory(list)
    keywords: List[str] = Factory(list)

    # pylint: disable=not-an-iterable
    @property
    def search_terms(self) -> Set[str]:
        """Return set of search terms for the object."""
        return set(
            [self.name]
            + [obj.casefold() for obj in self.entity_types]  # type: ignore
            + [key.casefold() for key in self.keywords]  # type: ignore
            + [opt.casefold() for opt in self.options]  # type: ignore
        )

    # pylint: enable=not-an-iterable

    def __str__(self):
        """Return string representation of object."""
        return "\n".join([f"{name}: {val}" for name, val in attr.asdict(self).items()])


class Notebooklet(ABC):
    """Base class for Notebooklets."""

    metadata: NBMetaData = NBMetaData(
        name="Notebooklet", description="Base class", options=[]
    )
    __doc__ += "\nAvailable options: " + ",".join(metadata.options)

    def __init__(
        self,
        data_providers: Optional[DataProviders] = None,
        query_provider: Optional[QueryProvider] = None,
        **kwargs
    ):
        """
        Intialize a new instance of the notebooklet class.

        Parameters
        ----------
        data_providers : DataProviders, Optional
            Optional DataProviders instance to query data.
            Most classes require this.
        query_provider : QueryProvider
            Optional query_provider instance to query data.
            Most classes require this.

        """
        self._kwargs = kwargs
        self.result: Optional[NotebookletResult] = None
        self.options: List[str] = []
        self.verbose: bool = kwargs.pop("verbose", False)
        self._set_tqdm_notebook(self.verbose)
        self._last_result: Optional[NotebookletResult] = None

        # pylint: disable=no-member
        self.data_providers = data_providers or DataProviders.current()  # type: ignore
        # pylint: enable=no-member
        if not self.data_providers:
            raise NotebookletException(
                "No current DataProviders instance was found.",
                "Please create an instance of msticnb."
            )
        self.query_provider = query_provider or self.data_providers.query_provider

    @abstractmethod
    def run(
        self,
        value: Any = None,
        data: Optional[pd.DataFrame] = None,
        timespan: Optional[TimeSpan] = None,
        options: Optional[Iterable[str]] = None,
        **kwargs,
    ) -> NotebookletResult:
        """
        Notebooklet abstract base class.

        Parameters
        ----------
        value : Any, optional
            value to process, by default None
        data : Optional[pd.DataFrame], optional
            Input data to process, by default None
        timespan : Optional[TimeSpan], optional
            Timespan over , by default None
        options :Optional[Iterable[str]], optional
            [description], by default None

        Returns
        -------
        NotebookletResult
            Result class from the notebooklet
        """
        if not options:
            self.options = self.metadata.options
        self.verbose = kwargs.pop("verbose", self.verbose)
        self._set_tqdm_notebook(self.verbose)
        return NotebookletResult()

    @classmethod
    def name(cls) -> str:
        """
        Return name of the Notebooklet.

        Returns
        -------
        str
            Name

        """
        return cls.metadata.name

    @classmethod
    def description(cls) -> str:
        """
        Return description of the Notebooklet.

        Returns
        -------
        str
            Description

        """
        return cls.metadata.description

    @classmethod
    def all_options(cls) -> List[str]:
        """
        Return supported options for Notebooklet run function.

        Returns
        -------
        List[str]
            Supported options.

        """
        return cls.metadata.options

    @classmethod
    def default_options(cls) -> List[str]:
        """
        Return default options for Notebooklet run function.

        Returns
        -------
        List[str]
            Supported options.

        """
        return cls.metadata.default_options

    @classmethod
    def keywords(cls) -> List[str]:
        """
        Return search keywords for Notebooklet.

        Returns
        -------
        List[str]
            Keywords

        """
        return cls.metadata.keywords

    @classmethod
    def entity_types(cls) -> List[str]:
        """
        Entity types supported by the notebooklet.

        Returns
        -------
        List[str]
            Entity names

        """
        return cls.metadata.entity_types

    @classmethod
    def match_terms(cls, search_terms: str) -> Tuple[bool, int]:
        """
        Search class definition for `search_terms`.

        Parameters
        ----------
        search_terms : str
            One or more search terms, separated by spaces
            or commas.
            Terms can be simple strings or regular expressions.

        Returns
        -------
        Tuple[bool, int]
            Returns a tuple of bool (True if all terms match)
            and int (count of matched terms)

        """
        search_text = " ".join(cls.metadata.search_terms)
        search_text += cls.__class__.__doc__ or ""
        match_count = 0
        terms = [
            subterm for term in search_terms.split(",")
            for subterm in term.split()
        ]
        for term in terms:
            if re.search(term, search_text, re.IGNORECASE):
                match_count += 1

        return (bool(match_count == len(terms)), match_count)

    @staticmethod
    def _set_tqdm_notebook(verbose=False):
        if verbose:
            tqdm.tqdm_notebook().pandas()