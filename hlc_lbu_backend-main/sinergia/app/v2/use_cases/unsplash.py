import os
import requests


UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')
UNSPLASH_API = os.getenv('UNSPLASH_API', 'https://api.unsplash.com')
UNSPLASH_UTM_SOURCE = os.getenv('UNSPLASH_UTM_SOURCE', 'your-app')
UNSPLASH_UTM_MEDIUM = os.getenv('UNSPLASH_UTM_MEDIUM', 'referral')


def _unsplash_headers():
    return {
        'Authorization': f'Client-ID {UNSPLASH_ACCESS_KEY}',
        'Accept-Version': 'v1'
    }


class SearchUnsplashUseCase(object):
    def execute(self, query, page=1, per_page=12, orientation=None, content_filter=None, color=None):
        if not UNSPLASH_ACCESS_KEY:
            return { 'ok': 0, 'message': { 'code': 'ECONF', 'text': 'UNSPLASH_ACCESS_KEY not configured' } }, 500

        params = {
            'query': query,
            'page': page,
            'per_page': per_page
        }
        if orientation: params['orientation'] = orientation
        if content_filter: params['content_filter'] = content_filter
        if color: params['color'] = color

        r = requests.get(f"{UNSPLASH_API}/search/photos", headers=_unsplash_headers(), params=params, timeout=30)
        if r.status_code != 200:
            return { 'ok': 0, 'message': { 'code': 'EUPI', 'text': r.text } }, r.status_code
        return r.json(), 200


class GetUnsplashPhotoUseCase(object):
    def execute(self, photo_id):
        if not UNSPLASH_ACCESS_KEY:
            return { 'ok': 0, 'message': { 'code': 'ECONF', 'text': 'UNSPLASH_ACCESS_KEY not configured' } }, 500

        r = requests.get(f"{UNSPLASH_API}/photos/{photo_id}", headers=_unsplash_headers(), timeout=30)
        if r.status_code != 200:
            return { 'ok': 0, 'message': { 'code': 'EUPI', 'text': r.text } }, r.status_code
        return r.json(), 200


class TrackUnsplashDownloadUseCase(object):
    def execute(self, download_location):
        if not UNSPLASH_ACCESS_KEY:
            return { 'ok': 0, 'message': { 'code': 'ECONF', 'text': 'UNSPLASH_ACCESS_KEY not configured' } }, 500

        r = requests.get(download_location, headers=_unsplash_headers(), timeout=30)
        if r.status_code not in (200, 204):
            return { 'ok': 0, 'message': { 'code': 'EUPI', 'text': r.text } }, r.status_code
        return { 'ok': 1 }, 200


def _with_utm(url: str) -> str:
    sep = '&' if ('?' in url) else '?'
    return f"{url}{sep}utm_source={UNSPLASH_UTM_SOURCE}&utm_medium={UNSPLASH_UTM_MEDIUM}"


class GetUnsplashAttributionUseCase(object):
    def execute(self, photo_id: str):
        if not UNSPLASH_ACCESS_KEY:
            return { 'ok': 0, 'message': { 'code': 'ECONF', 'text': 'UNSPLASH_ACCESS_KEY not configured' } }, 500

        r = requests.get(f"{UNSPLASH_API}/photos/{photo_id}", headers=_unsplash_headers(), timeout=30)
        if r.status_code != 200:
            return { 'ok': 0, 'message': { 'code': 'EUPI', 'text': r.text } }, r.status_code

        photo = r.json()
        user = photo.get('user', {})
        author_name = user.get('name', '')
        author_profile_url = (user.get('links', {}) or {}).get('html', '')
        photo_url = (photo.get('links', {}) or {}).get('html', '')

        author_link = _with_utm(author_profile_url) if author_profile_url else ''
        photo_link = _with_utm(photo_url) if photo_url else ''
        unsplash_home = _with_utm('https://unsplash.com')

        html = f"Photo by <a href=\"{author_link}\">{author_name}</a> on <a href=\"{unsplash_home}\">Unsplash</a>"

        payload = {
            'ok': 1,
            'data': {
                'text': f"Photo by {author_name} on Unsplash",
                'html': html,
                'links': {
                    'author': author_link,
                    'photo': photo_link,
                    'unsplash': unsplash_home
                },
                'author': {
                    'name': author_name,
                    'username': user.get('username', '')
                },
                'photo_id': photo_id
            }
        }
        return payload, 200


