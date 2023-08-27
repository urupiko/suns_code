import http.client  # httplibはPython3はhttp.clientへ移行
import httplib2
import os
import random
import time
import json
import pickle
import config

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

httplib2.RETRIES = 1
MAX_RETRIES = 10
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error,
                        IOError,
                        http.client.NotConnected,
                        http.client.IncompleteRead,
                        http.client.ImproperConnectionState,
                        http.client.CannotSendRequest,
                        http.client.CannotSendHeader,
                        http.client.ResponseNotReady,
                        http.client.BadStatusLine)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtubepartner"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


def get_authenticated_service():
    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.CLIENT_SECRETS_FILE, YOUTUBE_UPLOAD_SCOPE)
            creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)


def initialize_upload(youtube, options):
    tags = None
    if 'keywords' in options:
        tags = options['keywords'].split(",")

    body = dict(
        snippet=dict(
            title=options['title'],
            description=options['description'],
            tags=tags,
            categoryId=options['category']
        ),
        status=dict(
            privacyStatus=options['privacyStatus']
        )
    )

    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(options['file'], chunksize=-1, resumable=True)
    )

    video_id = resumable_upload(insert_request)

    if video_id is not None:
        insert_request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": config.PLAYLIST_ID,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        )
        response = insert_request.execute()
    
    return video_id


def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0
    id = None
    while response is None:
        try:
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    print("VIDEO_ID: %s" % response['id'])
                    id = response['id']
                else:
                    exit("The upload failed with an unexpected response: %s" % response)
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % \
                        (e.resp.status, e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e
        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
              exit("No longer attempting to retry.")
            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print("Sleeping %f seconds and then retrying..." % sleep_seconds)
            time.sleep(sleep_seconds)
    return id

def upload_video(options):
    if not os.path.exists(options['file']):
        exit("{options['file']}. is not found")

    youtube = get_authenticated_service()
    try:
        video_id = initialize_upload(youtube, options)
    except HttpError as e:
        print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))

    return video_id

def upload_thumbnail(target):
    infofile = os.path.join(target, 'info.json')
    with open(infofile, encoding='utf-8') as f:
        info = json.load(f)

    youtube = get_authenticated_service()

    request = youtube.thumbnails().set(
        videoId=info['video_id'],
        media_body=MediaFileUpload(os.path.join(target, 'thumbnail.jpg'))
    )
    response = request.execute()

    print(response)