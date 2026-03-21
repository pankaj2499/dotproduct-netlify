import json
import uuid as uuid_package
from dataclasses import asdict
from typing import Any, Generic, List, Literal, Mapping, Optional, Type, Union, overload

from weaviate.cluster import _Cluster
from weaviate.collections.aggregate import _AggregateCollection
from weaviate.collections.backups import _CollectionBackup
from weaviate.collections.batch.collection import (
    _BatchCollection,
    _BatchCollectionSync,
    _BatchCollectionWrapper,
)
from weaviate.collections.classes.dotproduct import ClusterSubmission
from weaviate.collections.classes.cluster import Shard
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES, MetadataQuery
from weaviate.collections.classes.internal import (
    CrossReferences,
    References,
    ReturnProperties,
    ReturnReferences,
    TReferences,
)
from weaviate.collections.classes.tenants import Tenant
from weaviate.collections.classes.types import Properties, TProperties
from weaviate.collections.config import _ConfigCollection
from weaviate.collections.data import _DataCollection
from weaviate.collections.generate import _GenerateCollection
from weaviate.collections.iterator import _IteratorInputs, _ObjectIterator
from weaviate.collections.query import _QueryCollection
from weaviate.collections.tenants import _Tenants
from weaviate.connect.v4 import ConnectionSync
from weaviate.dotproduct import DotproductStore, submit_cluster_workload
from weaviate.exceptions import UnexpectedStatusCodeError
from weaviate.types import UUID

from .base import _CollectionBase


class Collection(Generic[Properties, References], _CollectionBase[ConnectionSync]):
    """The collection class is the main entry point for interacting with a collection in Weaviate.

    This class is returned by the `client.collections.create` and `client.collections.get` methods. It provides
    access to all the methods available to you when interacting with a collection in Weaviate.

    You should not need to instantiate this class yourself but it may be useful to import this as a type when
    performing type hinting of functions that depend on a collection object.

    Attributes:
        aggregate: This namespace includes all the querying methods available to you when using Weaviate's standard aggregation capabilities.
        aggregate_group_by: This namespace includes all the aggregate methods available to you when using Weaviate's aggregation group-by capabilities.
        config: This namespace includes all the CRUD methods available to you when modifying the configuration of the collection in Weaviate.
        data: This namespace includes all the CUD methods available to you when modifying the data of the collection in Weaviate.
        generate: This namespace includes all the querying methods available to you when using Weaviate's generative capabilities.
        query_group_by: This namespace includes all the querying methods available to you when using Weaviate's querying group-by capabilities.
        query: This namespace includes all the querying methods available to you when using Weaviate's standard query capabilities.
        tenants: This namespace includes all the CRUD methods available to you when modifying the tenants of a multi-tenancy-enabled collection in Weaviate.
    """

    def __init__(
        self,
        connection: ConnectionSync,
        name: str,
        validate_arguments: bool,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
        properties: Optional[Type[Properties]] = None,
        references: Optional[Type[References]] = None,
    ) -> None:
        super().__init__(
            connection,
            name,
            validate_arguments,
            consistency_level,
            tenant,
        )
        self.__properties = properties
        self.__references = references

        self.__cluster = _Cluster(connection)

        config = _ConfigCollection(
            connection=connection,
            name=name,
            tenant=tenant,
        )

        self.aggregate: _AggregateCollection = _AggregateCollection(
            connection=connection,
            name=name,
            consistency_level=consistency_level,
            tenant=tenant,
            validate_arguments=validate_arguments,
        )
        """This namespace includes all the querying methods available to you when using Weaviate's standard aggregation capabilities."""
        self.backup: _CollectionBackup = _CollectionBackup(
            connection=connection,
            name=name,
        )
        """This namespace includes all the backup methods available to you when backing up a collection in Weaviate."""
        self.batch: _BatchCollectionWrapper[Properties] = _BatchCollectionWrapper[Properties](
            connection,
            consistency_level,
            name,
            tenant,
            config,
            batch_client=_BatchCollectionSync[Properties]
            if connection._weaviate_version.is_at_least(1, 36, 0)
            else _BatchCollection[Properties],
        )
        """This namespace contains all the functionality to upload data in batches to Weaviate for this specific collection."""
        self.config: _ConfigCollection = config
        """This namespace includes all the CRUD methods available to you when modifying the configuration of the collection in Weaviate."""
        self.data: _DataCollection[Properties] = _DataCollection[Properties](
            connection, name, consistency_level, tenant, validate_arguments
        )
        """This namespace includes all the CUD methods available to you when modifying the data of the collection in Weaviate."""
        self.generate: _GenerateCollection[Properties, References] = _GenerateCollection[
            Properties, References
        ](
            connection=connection,
            name=name,
            consistency_level=consistency_level,
            tenant=tenant,
            properties=properties,
            references=references,
            validate_arguments=validate_arguments,
        )
        """This namespace includes all the querying methods available to you when using Weaviate's generative capabilities."""
        self.query: _QueryCollection[Properties, References] = _QueryCollection[
            Properties, References
        ](
            connection=connection,
            name=name,
            consistency_level=consistency_level,
            tenant=tenant,
            properties=properties,
            references=references,
            validate_arguments=validate_arguments,
        )
        """This namespace includes all the querying methods available to you when using Weaviate's standard query capabilities."""
        self.tenants: _Tenants = _Tenants(
            connection=connection,
            name=name,
            validate_arguments=validate_arguments,
        )
        """This namespace includes all the CRUD methods available to you when modifying the tenants of a multi-tenancy-enabled collection in Weaviate."""

    def __len__(self) -> int:
        total = self.aggregate.over_all(total_count=True).total_count
        assert total is not None
        return total

    def __str__(self) -> str:
        config = self.config.get()
        json_ = json.dumps(asdict(config), indent=2)
        return f"<weaviate.Collection config={json_}>"

    def with_tenant(self, tenant: Union[str, Tenant]) -> "Collection[Properties, References]":
        """Use this method to return a collection object specific to a single tenant.

        If multi-tenancy is not configured for this collection then Weaviate will throw an error.

        This method does not send a request to Weaviate. It only returns a new collection object that is specific
        to the tenant you specify.

        Args:
            tenant: The tenant to use. Can be `str` or `wvc.tenants.Tenant`.
        """
        return Collection(
            connection=self._connection,
            name=self.name,
            validate_arguments=self._validate_arguments,
            consistency_level=self.consistency_level,
            tenant=tenant.name if isinstance(tenant, Tenant) else tenant,
            properties=self.__properties,
            references=self.__references,
        )

    def with_consistency_level(
        self, consistency_level: ConsistencyLevel
    ) -> "Collection[Properties, References]":
        """Use this method to return a collection object specific to a single consistency level.

        If replication is not configured for this collection then Weaviate will throw an error.

        This method does not send a request to Weaviate. It only returns a new collection object that is specific
        to the consistency level you specify.

        Args:
            consistency_level: The consistency level to use.
        """
        return Collection(
            connection=self._connection,
            name=self.name,
            validate_arguments=self._validate_arguments,
            consistency_level=consistency_level,
            tenant=self.tenant,
            properties=self.__properties,
            references=self.__references,
        )

    def insert(
        self,
        properties: Mapping[str, Any],
        *,
        references: Optional[Mapping[str, Any]] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[Any] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> uuid_package.UUID:
        """Insert an object into Weaviate and persist workload metadata in SQLite."""
        object_uuid = uuid_package.UUID(str(uuid)) if uuid is not None else uuid_package.uuid4()
        store = DotproductStore()
        store.upsert_object(
            uuid=str(object_uuid),
            collection=self.name,
            tenant=self.tenant,
            properties=properties,
            references=references,
            metadata=metadata,
            vector=vector,
            sync_status="pending",
        )
        try:
            inserted_uuid = self.data.insert(
                properties=properties,
                references=references,
                uuid=object_uuid,
                vector=vector,
            )
        except Exception:
            store.upsert_object(
                uuid=str(object_uuid),
                collection=self.name,
                tenant=self.tenant,
                properties=properties,
                references=references,
                metadata=metadata,
                vector=vector,
                sync_status="insert_failed",
            )
            raise

        store.upsert_object(
            uuid=str(inserted_uuid),
            collection=self.name,
            tenant=self.tenant,
            properties=properties,
            references=references,
            metadata=metadata,
            vector=vector,
            sync_status="synced",
        )
        return inserted_uuid

    def cluster(
        self,
        *,
        near_vector: Optional[Any] = None,
        near_object: Optional[UUID] = None,
        limit: int = 100,
        algorithm: str = "kmeans",
        params: Optional[Mapping[str, Any]] = None,
    ) -> ClusterSubmission:
        """Run a Weaviate search, store the candidate UUIDs, and enqueue a clustering workload."""
        if near_vector is not None and near_object is not None:
            raise ValueError("Provide either near_vector or near_object, not both")
        if limit < 1:
            raise ValueError("limit must be at least 1")

        if near_vector is not None:
            query = self.query.near_vector(
                near_vector=near_vector,
                limit=limit,
                return_metadata=MetadataQuery(distance=True),
            )
            query_payload = {"type": "near_vector", "limit": limit}
        elif near_object is not None:
            query = self.query.near_object(
                near_object=near_object,
                limit=limit,
                return_metadata=MetadataQuery(distance=True),
            )
            query_payload = {"type": "near_object", "limit": limit, "near_object": str(near_object)}
        else:
            query = self.query.fetch_objects(limit=limit)
            query_payload = {"type": "fetch_objects", "limit": limit}

        members = [
            (
                str(obj.uuid),
                getattr(obj.metadata, "distance", None) if obj.metadata is not None else None,
            )
            for obj in query.objects
        ]
        uuids = [uuid for uuid, _ in members]
        if not uuids:
            raise ValueError("Search returned no objects to cluster")

        store = DotproductStore()
        workload_id = store.create_cluster_workload(
            collection=self.name,
            tenant=self.tenant,
            algorithm=algorithm,
            params=dict(params or {}),
            query=query_payload,
            members=members,
        )
        task_id = submit_cluster_workload(workload_id)
        if task_id is not None:
            store.set_executor_task_id(workload_id, task_id)

        return ClusterSubmission(
            workload_id=workload_id,
            task_id=task_id,
            collection=self.name,
            uuids=uuids,
            status="queued",
        )

    def exists(self) -> bool:
        """Check if the collection exists in Weaviate."""
        try:
            self.config.get(simple=True)
            return True
        except UnexpectedStatusCodeError as e:
            if e.status_code == 404:
                return False
            raise e

    def shards(self) -> List[Shard]:
        """Get the statuses of all the shards of this collection.

        Returns:
            The list of shards belonging to this collection.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If weaviate reports a none OK status.
            weaviate.EmptyResponseError: If the response is empty.
        """
        return [
            shard
            for node in self.__cluster.nodes(self.name, output="verbose")
            for shard in node.shards
        ]

    @overload
    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None,
        after: Optional[UUID] = None,
        cache_size: Optional[int] = None,
    ) -> _ObjectIterator[Properties, References]: ...

    @overload
    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES,
        after: Optional[UUID] = None,
        cache_size: Optional[int] = None,
    ) -> _ObjectIterator[Properties, CrossReferences]: ...

    @overload
    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences],
        after: Optional[UUID] = None,
        cache_size: Optional[int] = None,
    ) -> _ObjectIterator[Properties, TReferences]: ...

    @overload
    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
        after: Optional[UUID] = None,
        cache_size: Optional[int] = None,
    ) -> _ObjectIterator[TProperties, References]: ...

    @overload
    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
        after: Optional[UUID] = None,
        cache_size: Optional[int] = None,
    ) -> _ObjectIterator[TProperties, CrossReferences]: ...

    @overload
    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
        after: Optional[UUID] = None,
        cache_size: Optional[int] = None,
    ) -> _ObjectIterator[TProperties, TReferences]: ...

    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
        after: Optional[UUID] = None,
        cache_size: Optional[int] = None,
    ) -> Union[
        _ObjectIterator[Properties, References],
        _ObjectIterator[Properties, CrossReferences],
        _ObjectIterator[Properties, TReferences],
        _ObjectIterator[TProperties, References],
        _ObjectIterator[TProperties, CrossReferences],
        _ObjectIterator[TProperties, TReferences],
    ]:
        """Use this method to return an iterator over the objects in the collection.

        This iterator keeps a record of the last object that it returned to be used in each subsequent call to
        Weaviate. Once the collection is exhausted, the iterator exits.

        If `return_properties` is not provided, all the properties of each object will be
        requested from Weaviate except for its vector as this is an expensive operation. Specify `include_vector`
        to request the vector back as well. In addition, if `return_references=None` then none of the references
        are returned. Use `wvc.QueryReference` to specify which references to return.

        Args:
            include_vector:     Whether to include the vector in the metadata of the returned objects.
            return_metadata:     The metadata to return with each object.
            return_properties:     The properties to return with each object.
            return_references:     The references to return with each object.
            after:     The cursor to use to mark the initial starting point of the iterator in the collection.
            cache_size:     How many objects should be fetched in each request to Weaviate during the iteration. The default is 100.

        Raises:
            weaviate.exceptions.WeaviateGRPCQueryError: If the request to the Weaviate server fails.
        """
        return _ObjectIterator(
            self.query,
            _IteratorInputs(
                include_vector=include_vector,
                return_metadata=return_metadata,
                return_properties=return_properties,
                return_references=return_references,
                after=after,
            ),
            cache_size=cache_size,
        )
