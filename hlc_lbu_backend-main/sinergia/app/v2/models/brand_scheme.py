source_schema = {
    'type': 'list',
    'empty': True,
    'schema': {
        'type': 'dict',
        'schema': {
            'page': {'type': ['string', 'integer'], 'empty': True, 'required': True, 'nullable': True},
            'type': {'type': 'string', 'empty': False, 'required': True},
            'value': {'type': 'string', 'empty': False, 'required': True}
        }
    }
}

sc_brand_save_valid = {
        'identity': {
        'type': 'dict', 
        'schema': {
            'values': {
                'type': 'dict',
                'schema': {
                    'value': {
                        'type': 'list', 
                        'empty': True, 
                        'required': True,
                        'schema': {
                            'type': 'string',
                            'empty': False,
                            'required': True
                        }
                    },
                    'source': source_schema
                }
            },
            'tone_voice': {
                'type': 'dict',
                'schema': {
                    'value': {
                        'type': 'list', 
                        'empty': True, 
                        'required': True,
                        'schema': {
                            'type': 'string',
                            'empty': False,
                            'required': True
                        }
                    },
                    'source': source_schema
                }
            },
            'vision': {
                'type': 'dict',
                'schema': {
                    'value': {'type': 'string', 'empty': True, 'required': True},
                    'source': source_schema
                }
            },
            'mission': {
                'type': 'dict',
                'schema': {
                    'value': {'type': 'string', 'empty': True, 'required': True},
                    'source': source_schema
                }
            },
            'about_us': {
                'type': 'dict',
                'schema': {
                    'value': {'type': 'string', 'empty': True, 'required': True},
                    'source': source_schema
                }
            },
        }
    },
    'logos': {
        'type': 'list',
        'empty': True,
        'schema': {
            'type': 'dict',
            'schema': {
                'id': {'type': 'integer', 'empty': False, 'required': True},
                'image_id': {'type': 'string', 'empty': False, 'required': True, 'nullable': True},
                'image_url': {'type': 'string', 'empty': True, 'required': False, 'nullable': True},
                'category': {'type': 'string', 'empty': False, 'required': True},
                'category_alias': {'type': 'string', 'empty': True, 'required': False, 'nullable': True},
                'description': {'type': 'string', 'empty': False, 'required': True},
                'source': source_schema
            }
        }
    },
    'colors': {
        'type': 'list',
        'empty': True,
        'schema': {
            'type': 'dict',
            'schema': {
                'id': {'type': 'integer', 'empty': False, 'required': True},
                'name': {'type': 'string', 'empty': False, 'required': True},
                'hex_code': {'type': 'string', 'empty': False, 'required': True},
                'category': {'type': 'string', 'empty': False, 'required': True},
                'source': source_schema
            }
        }
    },
    'dos_donts': {
        'type': 'list',
        'empty': True,
        'schema': {
            'type': 'dict',
            'schema': {
                'id': {'type': 'integer', 'empty': False, 'required': True},
                'type': {'type': 'string', 'empty': False, 'required': True},
                'rule': {'type': 'string', 'empty': False, 'required': True},
                'image_id': {'type': 'string', 'empty': True, 'required': False, 'nullable': True},
                'image_url': {'type': 'string', 'empty': True, 'required': False, 'nullable': True},
                'source': {**source_schema, 'required': False}
            }
        }
    },
    'typography': {
        'type': 'list',
        'empty': True,
        'schema': {
            'type': 'dict',
            'schema': {
                'id': {'type': 'integer', 'empty': False, 'required': True},
                'family': {'type': 'string', 'empty': False, 'required': True},
                'fonts': {
                    'type': 'list', 
                    'empty': True,
                    'schema': {
                        'type': 'dict',
                        'schema': {
                            'id': {'type': 'integer', 'empty': False, 'required': True},
                            'style': {'type': 'string', 'empty': False, 'required': True},
                            'usage': {'type': 'string', 'empty': False, 'required': True},
                            'file': {'type': 'string', 'empty': False, 'required': True, 'nullable': True},
                            'file_id': {'type': 'string', 'empty': False, 'required': True, 'nullable': True}
                        }
                    }
                }
            }
        }
    },
}

sc_brand_save_completed = {
        'identity': {
        'type': 'dict', 
        'schema': {
            'values': {
                'type': 'dict',
                'schema': {
                    'value': {
                        'type': 'list', 
                        'empty': False, 
                        'required': True,
                        'schema': {
                            'type': 'string',
                            'empty': False,
                            'required': True
                        }
                    },
                    'source': {'type': 'list', 'empty': True}
                }
            },
            'tone_voice': {
                'type': 'dict',
                'schema': {
                    'value': {
                        'type': 'list', 
                        'empty': False, 
                        'required': True,
                        'schema': {
                            'type': 'string',
                            'empty': False,
                            'required': True
                        }
                    },
                    'source': {'type': 'list', 'empty': True}
                }
            },
            'vision': {
                'type': 'dict',
                'schema': {
                    'value': {'type': 'string', 'empty': False, 'required': True},
                    'source': {'type': 'list', 'empty': True}
                }
            },
            'mission': {
                'type': 'dict',
                'schema': {
                    'value': {'type': 'string', 'empty': False, 'required': True},
                    'source': {'type': 'list', 'empty': True}
                }
            },
            'about_us': {
                'type': 'dict',
                'schema': {
                    'value': {'type': 'string', 'empty': False, 'required': True},
                    'source': {'type': 'list', 'empty': True}
                }
            },
        }
    },
    'logos': {
        'type': 'list',
        'empty': False,
        'schema': {
            'type': 'dict',
            'schema': {
                'id': {'type': 'integer', 'empty': False, 'required': True},
                'image_id': {'type': 'string', 'empty': False, 'required': True},
                'category': {'type': 'string', 'empty': False, 'required': True},
                'category_alias': {'type': 'string', 'empty': True, 'required': False},
                'description': {'type': 'string', 'empty': False, 'required': True},
                'source': {'type': 'list', 'empty': True}
            }
        }
    },
    'colors': {
        'type': 'list',
        'empty': False,
        'schema': {
            'type': 'dict',
            'schema': {
                'id': {'type': 'integer', 'empty': False, 'required': True},
                'name': {'type': 'string', 'empty': False, 'required': True},
                'hex_code': {'type': 'string', 'empty': False, 'required': True},
                'category': {'type': 'string', 'empty': False, 'required': True},
                'source': {'type': 'list', 'empty': True}
            }
        }
    },
    'dos_donts': {
        'type': 'list',
        'empty': False,
        'schema': {
            'type': 'dict',
            'schema': {
                'id': {'type': 'integer', 'empty': False, 'required': True},
                'image_id': {'type': 'string', 'empty': True, 'required': False},
                'type': {'type': 'string', 'empty': False, 'required': True},
                'rule': {'type': 'string', 'empty': False, 'required': True},
                'source': {'type': 'list', 'empty': True}
            }
        }
    },
    'typography': {
        'type': 'list',
        'empty': False,
        'schema': {
            'type': 'dict',
            'schema': {
                'id': {'type': 'integer', 'empty': False, 'required': True},
                'family': {'type': 'string', 'empty': False, 'required': True},
                'fonts': {
                    'type': 'list', 
                    'empty': True,
                    'schema': {
                        'type': 'dict',
                        'schema': {
                            'id': {'type': 'integer', 'empty': False, 'required': True},
                            'style': {'type': 'string', 'empty': False, 'required': True},
                            'usage': {'type': 'string', 'empty': False, 'required': True},
                            'file': {'type': 'string', 'empty': False, 'required': True},
                            'file_id': {'type': 'string', 'empty': False, 'required': True}
                        }
                    }
                }
            }
        }
    },
}