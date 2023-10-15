source envManga/bin/activate
if [ -z "$1" ]; then
    echo Title needed
else
    echo Title: $1
    python manga.py "$1" --single --format EPUB
fi
deactivate