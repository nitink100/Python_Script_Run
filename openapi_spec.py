# openapi_spec.py
# Minimal, accurate OpenAPI 3.0 spec for your current endpoints.
# No external dependencies required.

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Safe Python Execution Service",
        "version": "1.0.0",
        "description": (
            "Execute untrusted Python snippets with strict limits. "
            "Endpoints: /health, /execute"
        ),
    },
    "servers": [{"url": "/"}],
    "paths": {
        "/health": {
            "get": {
                "summary": "Health check",
                "responses": {
                    "200": {
                        "description": "Service OK",
                        "content": {
                            "application/json": {
                                "schema": {"type": "object", "properties": {"ok": {"type": "boolean"}}}
                            }
                        },
                    }
                },
            }
        },
        "/execute": {
            "post": {
                "summary": "Execute a Python script defining main()",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ExecuteRequest"}
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Execution result",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ExecuteSuccess"}
                            }
                        },
                    },
                    "400": {
                        "description": "Validation error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorEnvelope"}
                            }
                        },
                    },
                    "408": {
                        "description": "Execution timed out",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorEnvelope"}
                            }
                        },
                    },
                    "500": {
                        "description": "Internal error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorEnvelope"}
                            }
                        },
                    },
                },
            }
        },
    },
    "components": {
        "schemas": {
            "ExecuteRequest": {
                "type": "object",
                "required": ["script"],
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "Python source string that defines a callable main()"
                    }
                },
                "additionalProperties": False,
            },
            "ExecuteSuccess": {
                "type": "object",
                "properties": {
                    "result": {
                        "description": "JSON-serializable return value from main()",
                    },
                    "stdout": {"type": "string"},
                },
                "required": ["result", "stdout"],
                "additionalProperties": False,
            },
            "ErrorEnvelope": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": (
                                    "Machine-readable code. Possible values: "
                                    "BAD_CONTENT_TYPE, BAD_BODY, BAD_SCRIPT, BAD_ENCODING, BAD_INPUT, "
                                    "SCRIPT_TOO_LARGE, SYNTAX_ERROR, NO_MAIN, TIMEOUT, EMPTY_OUTPUT, "
                                    "IMPORT_ERROR, INVALID_MAIN, EXCEPTION, NON_JSON_RETURN, BAD_RUNNER_OUTPUT"
                                )
                            },
                            "message": {"type": "string"},
                            "details": {"type": "object", "additionalProperties": True},
                        },
                        "required": ["code", "message"],
                        "additionalProperties": False,
                    }
                },
                "required": ["error"],
                "additionalProperties": False,
            },
        }
    },
}
