#!/usr/bin/env python3
import mistune
import os
import uuid
import yaml
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from glob import glob
from multiprocessing import Pool
from PIL import Image

def mkdir_p(path):
    """Like mkdir -p"""
    try:
        os.makedirs(path)
    except:
        pass

def thumbnail(image):
    """Generate and return a thumbnail from an image."""
    width, height = image.size
    if width > height:
        pad = width - height
        x0 = pad // 2
        y0 = 0
        x1 = height + x0
        y1 = height
    else:
        pad = height - width
        x0 = 0
        y0 = pad // 2
        x1 = width
        y1 = width + y0
    image = image.crop((x0, y0, x1, y1))
    image.thumbnail(thumbsize, Image.ANTIALIAS)
    return image

def newer(a, b):
    """Return true if b exists and is older than a."""
    return (not os.path.exists(b) or 
            os.path.getmtime(a) > os.path.getmtime(b))

def link(a, b):
    """Like ln -f."""
    if os.path.exists(b):
        os.unlink(b)
    os.link(a, b)

def loadmeta(file):
    """Load all of the metadata (YAML, Markdown) for an image."""
    with open(file, 'r', encoding='utf-8') as md:
        lines = [md.readline()]
        while True:
            line = md.readline()
            if line.startswith('---'):
                break;
            lines.append(line)
        meta = yaml.load(''.join(lines))
        html = mistune.markdown(''.join(md.readlines())) 
        dom = BeautifulSoup(html, 'html.parser')
        meta['content'] = dom
        meta['file'] = file
        return meta

def getpagepath(md):
    """Return the page URL for a given photo."""
    return '/' + os.path.splitext(md['file'])[0] + '/'

def feed_add(md, title=None, href=None, content=None):
    """Add an entry to the current feed."""
    if not title:
        title = md['title']
    if not href:
        href = getpagepath(md)
    if not content:
        content = str(md['content'])
    url = baseurl + href
    entry = feed.new_tag('entry')
    tag_title = feed.new_tag('title')
    tag_title.string = title
    tag_id = feed.new_tag('id')
    tag_id.string = 'urn:uuid:' + str(uuid.uuid3(uuid.NAMESPACE_URL, url))
    tag_link = feed.new_tag('link')
    tag_link.attrs['rel'] = 'alternate'
    tag_link.attrs['type'] = 'text/html'
    tag_link.attrs['href'] = url
    tag_updated = feed.new_tag('updated')
    tag_updated.string = md['date'].isoformat() + 'Z'
    tag_content = feed.new_tag('content')
    tag_content.attrs['type'] = 'html'
    tag_content.string = content
    entry.append(tag_title)
    entry.append(tag_id)
    entry.append(tag_link)
    entry.append(tag_updated)
    entry.append(tag_content)
    feed_feed.append(entry)

def gallery_add(md, title=None, href=None):
    """Add an image to the current gallery."""
    pagepath = getpagepath(md)
    if not title:
        title = md['title']
    if not href:
        href = pagepath
    thumbpath = pagepath + 'thumb.jpg'
    li = gallery.new_tag('li')
    h2 = gallery.new_tag('h2')
    h2.string = title
    li.append(h2)
    img = gallery.new_tag('img')
    img.attrs['src'] = thumbpath
    img.attrs['alt'] = ''
    img.attrs['title'] = title
    img.attrs['width'] = str(thumbsize[0])
    img.attrs['height'] = str(thumbsize[1])
    a = gallery.new_tag('a')
    a.attrs['href'] = href;
    a.append(img)
    li.append(a)
    gallery_gallery.append(li)

def gengallery(base, mdfiles):
    """Generate a brand new photo gallery."""
    conffile = base[1:] + '/_gallery.yaml'
    if os.path.exists(conffile):
        with open(conffile, 'r', encoding='utf-8') as file:
            conf = yaml.load(file)
        title = conf['title']
    elif base == '/':
        title = site_title
    else:
        title = base

    # Fill out gallery details
    for a in gallery_gallery.select('li'):
        a.decompose()
    if base == '/':
        gallery_title.string = site_title
    else:
        gallery_title.string = title + ' » ' + site_title
    gallery_h1.string = title

    # Fill out Atom feed details
    feed_title.string = title + ' » ' + site_title
    gallery_uuid = uuid.uuid3(uuid.NAMESPACE_URL, baseurl + base)
    feed_id.string = 'urn:uuid:' + str(gallery_uuid)
    for entry in feed.select('entry'):
        entry.decompose()

    # Process each image in the gallery
    for i in range(len(mdfiles)):
        md = mdfiles[i]
        feed_add(md)
        mdfile = md['file']
        pagepath = getpagepath(md)
        imagefile = os.path.splitext(mdfile)[0] + '.jpg'
        thumbpath = pagepath + 'thumb.jpg'
        previewpath = pagepath + 'preview.jpg'
        thumbfile = output + thumbpath
        previewfile = output + previewpath
        fullpath = '../' + os.path.basename(imagefile)

        ## Only create single page when building root gallery
        if base == '/':
            # Create thumbnail
            if newer(imagefile, thumbfile) or newer(imagefile, previewfile):
                thumbqueue.append((imagefile, thumbfile, previewfile))
                mkdir_p(os.path.dirname(thumbfile))
                mkdir_p(os.path.dirname(previewfile))

            # Create page for image
            single_title.string = md['title']
            single_full.attrs['href'] = fullpath
            single_img.attrs['src'] = 'preview.jpg'
            if i > 0:
                single_prev.attrs['href'] = getpagepath(mdfiles[i - 1])
            else:
                single_prev.attrs['href'] = '#'
            if i < len(mdfiles) - 1:
                single_next.attrs['href'] = getpagepath(mdfiles[i + 1])
            else:
                single_next.attrs['href'] = '#'
            single_h1.string = md['title']
            single_time.string = md['date'].strftime('%B %d, %Y')
            single_time.attrs['datetime'] = md['date'].isoformat() + 'Z'
            single_info.string = ''
            single_info.append(md['content'])
            if md.get('f-stop'):
                single_fstop.string = md['f-stop']
            else:
                single_fstop.string = ''
            if md.get('exposure-time'):
                single_exposure.string = md['exposure-time']
            else:
                single_exposure.string = ''
            if md.get('iso'):
                single_iso.string = str(md['iso'])
            else:
                single_iso.string = ''
            indexfile = output + pagepath + 'index.html';
            mkdir_p(output + pagepath)
            with open(indexfile, 'w', encoding='utf-8') as file:
                file.write(single.prettify())

        # Create link in gallery
        gallery_add(md)

    # Write out generated index
    indexfile = output + base + '/index.html'
    with open(indexfile, 'w', encoding='utf-8') as file:
        file.write(gallery.prettify())

    # Write out generated feed
    mkdir_p(output + base + '/feed')
    if base == '/':
        feed_self.attrs['href'] = baseurl + '/feed/'
    else:
        feed_self.attrs['href'] = baseurl + base + '/feed/'
    with open(output + base + '/feed/index.xml', 'w', encoding='utf-8') as file:
        file.write(str(feed))

def derive_images(val):
    """Generate thumbnail and preview images (multiprocessing)."""
    (imagefile, thumbfile, previewfile) = val
    image = Image.open(imagefile)
    thumbnail(image).save(thumbfile)
    image.thumbnail(previewsize)
    image.save(previewfile)

# Exit when we're a multiprocessing child
if __name__ != '__main__':
    exit(0)

# Load site configuration
with open('_config.yaml', 'r', encoding='utf-8') as file:
    config = yaml.load(file)
site_title = config['title']
author = config['author']
baseurl = config['baseurl']
output = config['output']
thumbsize = (config['thumbsize'], config['thumbsize'])
previewsize = (config['previewsize'], config['previewsize'])

# List of thumbnails and previews to create
thumbqueue = []

# Load the gallery template
gallery = BeautifulSoup(open('_gallery.html', encoding='utf-8'), 'lxml')
gallery_title = gallery.select('title')[0]
gallery_gallery = gallery.select('#gallery')[0]
gallery_h1 = gallery.select('#title')[0]
gallery_h1.string = site_title

# Load the image page template
single = BeautifulSoup(open('_single.html', encoding='utf-8'), 'lxml')
single_title = single.select('title')[0]
single_full = single.select('#full')[0]
single_img = single.select('#photo')[0]
single_prev = single.select('#prev')[0]
single_next = single.select('#next')[0]
single_h1 = single.select('#title')[0]
single_time = single.select('time')[0]
single_info = single.select('#info')[0]
single_fstop = single.select('#f-stop')[0]
single_exposure = single.select('#exposure-time')[0]
single_iso = single.select('#iso')[0]

# Load the feed template
feed = BeautifulSoup(open('_feed.xml', encoding='utf-8'), 'xml')
feed_feed = feed.select('feed')[0]
feed_title = feed.select('title')[0]
feed_author = feed.select('author name')[0]
feed_author.string = author
feed_updated = feed.select('feed > updated')[0]
feed_updated.string = datetime.now(timezone.utc).astimezone().isoformat()
feed_id = feed.select('feed > id')[0]
feed_self = feed.select('feed link[rel="self"]')[0]

# Dumb copy over files
files = glob('**/*', recursive=True)
for file in files:
    if os.path.isfile(file) and file[0] != '_':
        dest = output + '/' + file
        mkdir_p(os.path.dirname(dest))
        link(file, dest)

# Gather a list of all images
mdfiles = glob('**/*.md', recursive=True)
mdfiles = filter(lambda md: not md.startswith("_"), mdfiles)
mdfiles = map(loadmeta, mdfiles)
mdfiles = sorted(mdfiles, key=lambda md: md['date'], reverse=True)

# Gather up all the galleries
galleries = {}
galleries['/'] = mdfiles
for md in mdfiles:
    base = '/' + os.path.dirname(md['file'])
    if not galleries.get(base):
        galleries[base] = []
    galleries[base].append(md)

# Generate album listing
gallery_title.string = 'List of Albums » ' + site_title
gallery_h1.string = 'List of Albums'
feed_title.string = 'List of Albums » ' + site_title
listing_uuid = uuid.uuid3(uuid.NAMESPACE_URL, baseurl + '/albums/')
feed_id.string = 'urn:uuid:' + str(listing_uuid)
for name in sorted(galleries.keys()):
    if name != '/':
        md = galleries[name][-1]
        conffile = name[1:] + '/_gallery.yaml'
        if os.path.exists(conffile):
            with open(conffile, 'r', encoding='utf-8') as file:
                conf = yaml.load(file)
                title = conf['title']
                if conf.get('image'):
                    for image in galleries[name]:
                        if image['title'] == conf['image']:
                            md = image
        else:
            title = name
        gallery_add(md, title=title, href=name + '/')
        feed_add(md, title=title, href=name + '/')

# Write out albums HTML and feed
listing_path = output + '/albums'
mkdir_p(listing_path)
with open(listing_path + '/index.html', 'w', encoding='utf-8') as file:
    file.write(gallery.prettify())
listing_feed_path = output + '/albums/feed'
mkdir_p(listing_feed_path)
feed_self.attrs['href'] = baseurl + '/albums/feed/'
with open(listing_feed_path + '/index.xml', 'w', encoding='utf-8') as file:
    file.write(str(feed))

# Generate the main gallery
for base, mdfiles in galleries.items():
    gengallery(base, mdfiles)

# Spawn subprocesses to create thumbnails and previews
with Pool() as pool:
    pool.map(derive_images, thumbqueue, 1)
