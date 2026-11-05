from app.v2.use_cases.ad import AbyssaleVisualEditUseCase


class DummyAbyssaleVisualAdChannelRepository:
    def __init__(self, mapping):
        self.mapping = mapping
        self.seen_sharing_id = None

    def get_by_sharing_id(self, sharing_id):
        self.seen_sharing_id = sharing_id
        return self.mapping


class DummyAdChannelRepository:
    def __init__(self):
        self.updated = []

    def update(self, ad_channel_id, data):
        self.updated.append((ad_channel_id, data))
        return {'id': ad_channel_id, 'attributes': data}


def test_execute_updates_matching_media_format_and_preserves_other_fields():
    payload = {
        'id': 'visual-123',
        'sharing_id': 'sharing-1',
        'file': {'url': 'https://cdn.example/image.jpg'},
    }

    ad_channel_data = {
        'id': 77,
        'attributes': {
            'media_formats': [
                {
                    'id': 'instagram-portrait',
                    'sharing_id': 'sharing-1',
                    'visual_url': 'old-url',
                    'visual_id': 'old-id',
                },
                {
                    'id': 'facebook-post',
                    'sharing_id': 'sharing-2',
                    'visual_url': 'other-url',
                    'visual_id': 'other-id',
                },
            ],
            'name': 'Existing ad',
        },
    }

    mapping = {
        'id': 10,
        'attributes': {
            'sharing_id': 'sharing-1',
            'ad_channel': {'data': ad_channel_data},
        },
    }

    use_case = AbyssaleVisualEditUseCase()
    use_case.abyssale_visual_repo = DummyAbyssaleVisualAdChannelRepository(mapping)
    use_case.ad_channel_repo = DummyAdChannelRepository()

    result = use_case.execute(payload)

    assert result == {'ok': True}
    assert use_case.abyssale_visual_repo.seen_sharing_id == 'sharing-1'
    assert len(use_case.ad_channel_repo.updated) == 1
    ad_channel_id, updated_data = use_case.ad_channel_repo.updated[0]
    assert ad_channel_id == 77
    assert set(updated_data.keys()) == {'media_formats'}
    assert updated_data['media_formats'][0]['visual_url'] == 'https://cdn.example/image.jpg'
    assert updated_data['media_formats'][0]['visual_id'] == 'visual-123'
    assert updated_data['media_formats'][1]['sharing_id'] == 'sharing-2'
    assert updated_data['media_formats'][1]['visual_url'] == 'other-url'
