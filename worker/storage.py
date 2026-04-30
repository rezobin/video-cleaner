from app.supabase_client import supabase

def download(path: str):
    return supabase.storage.from_("videos").download(path)


def upload(path: str, file_obj):
    return supabase.storage.from_("videos").upload(
        path=path,
        file=file_obj,
        file_options={"content-type": "video/mp4", "upsert": "true"}
    )


def public_url(path: str):
    return supabase.storage.from_("videos").get_public_url(path)


import requests

def get_signed_url(path: str):
    res = supabase.storage.from_("videos").create_signed_url(path, 3600)
    return res["signedURL"]