from app.v2.use_cases.image_library import GetProductImagesUseCase


class DummyProductRepository:
    def __init__(self, product):
        self.product = product

    def get_by_id(self, product_id):
        return self.product


class DummyProductImageRepository:
    def __init__(self, images):
        self.images = images

    def get_by_product_id(self, product_id):
        return self.images


class DummyImageLibraryRepository:
    def __init__(self, image_map):
        self.image_map = image_map

    def get_image(self, image_id):
        return self.image_map.get(image_id, {})


def test_get_product_images_use_case_returns_urls_for_each_product_image():
    use_case = GetProductImagesUseCase()
    use_case.product_repository = DummyProductRepository({'id': 1, 'attributes': {}})
    use_case.product_image_repository = DummyProductImageRepository([
        {'id': 11, 'attributes': {'image_id': 'img-1'}},
        {'id': 12, 'attributes': {'image_id': 'img-2'}},
        {'id': 13, 'attributes': {'image_id': None}},
    ])
    use_case.image_library_repository = DummyImageLibraryRepository({
        'img-1': {'url': 'https://cdn.example/img-1.jpg'},
        'img-2': {'url': 'https://cdn.example/img-2.jpg'},
    })

    result = use_case.execute(1)

    assert result == [
        {'url': 'https://cdn.example/img-1.jpg'},
        {'url': 'https://cdn.example/img-2.jpg'},
    ]
