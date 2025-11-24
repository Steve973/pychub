from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Type, TypeVar

from pychub.helper.toml_utils import load_toml_text

T = TypeVar("T", bound="MultiformatDeserializableMixin")


class MultiformatDeserializableMixin:
    """
    A mixin class that provides deserialization capabilities from multiple formats like JSON, YAML, and TOML.

    Details:
        This mixin enables subclasses to deserialize data from different text-based serialization formats
        into Python objects. Subclasses must implement the `from_mapping` method to specify how to build
        an instance from a mapping. The mixin also provides hook methods to allow customizing the
        deserialization steps, such as preprocessing mappings or postprocessing instances.
    """

    # ---- core contract ----

    @classmethod
    def from_mapping(cls: Type[T], mapping: Mapping[str, Any], **_: Any) -> T:
        """
        A factory method responsible for creating an instance of the class from a given mapping. This method is intended to
        be implemented by subclasses.

        Args:
            mapping (Mapping[str, Any]): A collection or object that maps strings to any type of value.
            **_ (Any): Additional keyword arguments for extensibility in derived implementations.

        Raises:
            NotImplementedError: Raised if this base method is not overridden by a subclass providing the specific
            implementation.
        """
        raise NotImplementedError(
            f"{cls.__name__} must implement from_mapping(mapping, **kwargs) "
            "to use MultiformatDeserializableMixin.")

    # ---- public entrypoints ----

    @classmethod
    def deserialize(cls: Type[T], text: str, *, fmt: str = "json", **context: Any) -> T:
        """
        Deserializes a given text representation into an instance of the class.

        This method processes the text input based on the specified format, ensuring
        the data is parsed, coerced into a mapping structure, and optionally preprocessed
        before creating an instance of the class. Finally, a postprocessing step is
        performed on the created instance to finalize its state.

        Args:
            text (str): The string representation of the object to be deserialized.
            fmt (str, optional): The format in which the input text is given. Defaults to "json".
            **context (Any): Additional context or parameters that might be necessary
                for parsing or instantiation.

        Returns:
            T: An instance of the class created using the deserialized data.
        """
        raw = cls._parse_text(text, fmt=fmt, path=None, **context)
        mapping = cls._coerce_root_mapping(raw, fmt=fmt, path=None, **context)
        mapping = cls._preprocess_mapping(mapping, fmt=fmt, path=None, **context)
        inst = cls.from_mapping(mapping, **context)
        return cls._postprocess_instance(inst, fmt=fmt, path=None, **context)

    @classmethod
    def from_json(cls: Type[T], text: str, **context: Any) -> T:
        """
        Creates an instance of the class by deserializing a JSON-formatted string.

        This class method processes a JSON string to create and return an instance
        of the class. The deserialization is performed using the provided JSON string
        and any additional context-specific arguments required for customization.

        Args:
            text (str): The JSON string to be deserialized.
            **context (Any): Additional context or parameters to be passed for
                deserialization.

        Returns:
            T: An instance of the class initialized with data from the JSON string.
        """
        return cls.deserialize(text, fmt="json", **context)

    @classmethod
    def from_yaml(cls: Type[T], text: str, **context: Any) -> T:
        """
        Creates an instance of the class by deserializing a YAML string.

        This method is a class method that takes a YAML string and optional
        additional context as input. It then deserializes the string into an
        instance of the class.

        Args:
            text: The YAML string to be deserialized.
            **context: Arbitrary keyword arguments that may provide additional
                context or configuration for the deserialization.

        Returns:
            An instance of the class (`T`) created using the deserialized data.
        """
        return cls.deserialize(text, fmt="yaml", **context)

    @classmethod
    def from_toml(cls: Type[T], text: str, **context: Any) -> T:
        """
        Creates an instance of the class by deserializing data in TOML format.

        This method is a class method that allows creating an instance of the class
        by providing a TOML-encoded input and optional context parameters for
        deserialization.

        Args:
            text (str): The TOML-formatted string to be deserialized into an
                instance of the class.
            **context (Any): Additional context parameters that may be utilized
                during the deserialization process.

        Returns:
            T: An instance of the class created by deserializing the provided
                TOML-formatted data.
        """
        return cls.deserialize(text, fmt="toml", **context)

    @classmethod
    def from_file(cls: Type[T], path: str | Path, fmt: str | None = None, **context: Any) -> T:
        """
        Creates an instance of the class from a file specified by the provided path.

        This method loads text from the given file path, determines the format if not
        explicitly provided, parses the text, coerces it into an internal mapping, and
        preprocesses it before creating an instance. After creating the instance,
        postprocessing is applied before returning the final object.

        Args:
            path (str | Path): A string or `Path` object specifying the file's path.
            fmt (str | None): The format of the file content. If None, the format will
                be inferred automatically from the file's suffix.
            **context (Any): Additional context data or configuration that might
                influence the parsing and creation process.

        Returns:
            T: An instance of the class.
        """
        p = Path(path)
        text = cls._load_text(p, **context)
        fmt = fmt or cls._infer_format_from_suffix(p)
        raw = cls._parse_text(text, fmt=fmt, path=p, **context)
        mapping = cls._coerce_root_mapping(raw, fmt=fmt, path=p, **context)
        mapping = cls._preprocess_mapping(mapping, fmt=fmt, path=p, **context)
        inst = cls.from_mapping(mapping, **context)
        return cls._postprocess_instance(inst, fmt=fmt, path=p, **context)

    # ---- overridable hooks ----

    @classmethod
    def _load_text(cls, path: Path, **_: Any) -> str:
        """
        Loads text from a given file path.

        This method reads the content of a file located at the given `path` and
        returns it as a string. The file is assumed to be encoded in UTF-8.

        Args:
            path (Path): The path to the file from which text will be loaded.
            **_ (Any): Additional keyword arguments that are ignored.

        Returns:
            str: The content of the file as a string.
        """
        return path.read_text(encoding="utf-8")

    @classmethod
    def _infer_format_from_suffix(cls, path: Path) -> str:
        """
        Infers the file format based on the suffix of the given file path.

        This method analyzes the suffix of the file to determine the format.
        Supported formats are JSON, YAML, and TOML. If the suffix does not match
        any of the supported formats, it raises a ValueError.

        Args:
            path (Path): The file path to infer the format from.

        Returns:
            str: The inferred format as a string ("json", "yaml", or "toml").

        Raises:
            ValueError: If the file suffix is not recognized as a supported format.
        """
        suffix = path.suffix.lower()
        match suffix:
            case ".json":
                return "json"
            case ".yaml" | ".yml":
                return "yaml"
            case ".toml":
                return "toml"
            case _:
                raise ValueError(f"Cannot infer format from extension {suffix!r}")

    @classmethod
    def _parse_text(cls, text: str, *, fmt: str, path: Path | None, **_: Any) -> Any:
        """
        Parses text content into a data structure based on the specified format.

        This method supports parsing text content in JSON, YAML, or TOML format.
        If the format specified is unsupported or invalid, it raises an
        appropriate exception.

        Args:
            text (str): The text content to be parsed.
            fmt (str): The format of the text content. Supported values are
                "json", "yaml", and "toml". Case is ignored.
            path (Path | None): Reserved for potential future use, currently not utilized.
            **_ (Any): Additional keyword parameters, ignored.

        Returns:
            Any: The parsed data structure derived from the input text.

        Raises:
            RuntimeError: If the format is "yaml" and the PyYAML library is not installed.
            ValueError: If the format is unrecognized or unsupported.
        """
        fmt = fmt.lower()
        match fmt:
            case "json":
                import json
                return json.loads(text or "{}")
            case "yaml":
                try:
                    import yaml
                except ImportError:
                    raise RuntimeError("PyYAML not installed")
                return next(iter(yaml.safe_load_all(text)), None) or {}
            case "toml":
                return load_toml_text(text or "")
            case _:
                raise ValueError(f"unrecognized format: {fmt!r}")

    @classmethod
    def _coerce_root_mapping(
            cls,
            raw: Any,
            *,
            fmt: str,
            path: Path | None,
            **_: Any) -> Mapping[str, Any]:
        """
        Coerces a given raw input into a mapping type if valid.

        This method ensures that the provided `raw` object is a mapping type. If it is
        not, a TypeError will be raised. It is typically used to validate and process
        data inputs.

        Args:
            raw: The input to be validated as a mapping type.
            fmt: A string representing the format or source of the input,
                used for error reporting.
            path: A Path object or None indicating the filepath associated with the
                input, used for error reporting.
            **_: Additional keyword arguments that are ignored during processing.

        Returns:
            Mapping[str, Any]: The validated input as a mapping type.

        Raises:
            TypeError: If the provided input is not a mapping type.
        """
        if isinstance(raw, Mapping):
            return raw
        raise TypeError(
            f"{cls.__name__} expected top-level mapping, got {type(raw)!r} "
            f"from {fmt} {str(path) if path else '<inline>'}")

    @classmethod
    def _preprocess_mapping(
            cls,
            mapping: Mapping[str, Any],
            *,
            fmt: str,
            path: Path | None,
            **_: Any) -> Mapping[str, Any]:
        """
        Preprocesses a given mapping according to specific requirements. This method can be overridden
        in subclasses to handle unique preprocessing cases. By default, it passes the mapping through
        unchanged.

        Args:
            mapping (Mapping[str, Any]): The input mapping to preprocess.
            fmt (str): The format to be applied during preprocessing.
            path (Path | None): The file path relevant to the preprocessing, if any.
            **_ (Any): Additional arguments that might be passed but are ignored by default.

        Returns:
            Mapping[str, Any]: The processed mapping, identical to the input by default.
        """
        # default: pass-through; override in unique cases
        return mapping

    @classmethod
    def _postprocess_instance(
            cls,
            inst: T,
            *,
            fmt: str,
            path: Path | None,
            **_: Any) -> T:
        """
        Post-process an instance after its creation. This method performs any
        necessary modifications, validations, or derivations on the instance
        before returning it. By default, this is a pass-through operation, but
        it can be overridden in subclasses to implement custom behavior.

        Processes the given instance by setting the 'source_description' attribute
        based on the provided format and path if the attribute exists and is
        currently empty or falsey. This operation does not modify the value if it
        already holds a truthy value.

        If a subclass overrides this method and still wants the default behavior,
        it can call super()._postprocess_instance(...) and then apply additional
        logic.

        Args:
            inst: The instance to be post-processed.
            fmt: A string representing the format that may guide the
                post-processing operations.
            path: An optional path of type Path which may be used for
                additional processing context.
            **_: Additional keyword arguments that might be absorbed without
                explicit use in the default implementation.

        Returns:
            The post-processed instance of the same type as the input.
        """
        # Soft opt-in: only touch if the attribute exists and is empty/falsey
        if hasattr(inst, "source_description"):
            current = getattr(inst, "source_description", None)
            if not current:
                if path is not None:
                    desc = f"{fmt}:{path}"
                else:
                    desc = f"{fmt}:<inline>"
                try:
                    setattr(inst, "source_description", desc)
                except Exception:
                    # Don't blow up if the subclass does something naughty (oh, behave!)
                    pass

        return inst
