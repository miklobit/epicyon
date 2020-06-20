<blockquote><b>Epicyon</b>, meaning <i>"more than a dog"</i>. Largest of the <i>Borophaginae</i> which lived in North America 20-5 million years ago.</blockquote>

<img src="https://code.freedombone.net/bashrc/epicyon/raw/master/img/mobile.jpg?raw=true" width="30%"/>

Epicyon is a modern [ActivityPub](https://www.w3.org/TR/activitypub) compliant server implementing both S2S and C2S protocols and sutable for installation on single board computers. It includes features such as moderation tools, post expiry, content warnings, image descriptions and perimeter defense against adversaries.

[Project Goals](README_goals.md) - [Commandline interface](README_commandline.md) - [Customizations](README_customizations.md) - [Object Capabilities](ocaps.md) - [Code of Conduct](code-of-conduct.md)

Matrix room: **#epicyon:matrix.freedombone.net**

Includes emojis designed by [OpenMoji](https://openmoji.org) – the open-source emoji and icon project. License: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0). Blob Cat Emoji and Meowmoji were made by Nitro Blob Hub, licensed under [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0).

<img src="https://code.freedombone.net/bashrc/epicyon/raw/main/img/screenshot_light.jpg" width="80%"/>

## Package Dependencies

You will need python version 3.7 or later.

On Arch/Parabola:

``` bash
sudo pacman -S tor python-pip python-pysocks python-pycryptodome \
               imagemagick python-pillow python-requests \
	       perl-image-exiftool python-numpy python-dateutil \
	       python-qrcode python-png certbot flake8
suso pip3 install pyLD
```

Or on Debian:

``` bash
sudo apt install -y \
    tor python3-socks imagemagick \
    python3-numpy python3-setuptools \
    python3-crypto python3-pycryptodome \
    python3-dateutil python3-pil.imagetk
    python3-idna python3-requests \
    python3-pyld python3-django-timezone-field \
    libimage-exiftool-perl python3-flake8 \
    python3-pyqrcode python3-png certbot nginx
```

## Installation

In the most common case you'll be using systemd to set up a daemon to run the server.

The following instructions install Epicyon to the **/etc** directory. It's not essential that it be installed there, and it could be in any other preferred directory.

Add a dedicated user so that we don't have to run as root.

``` bash
adduser --system --home=/opt/epicyon --group epicyon
```

Edit */etc/systemd/system/epicyon.service* and add the following:

``` systemd
[Unit]
Description=epicyon
After=syslog.target
After=network.target

[Service]
Type=simple
User=epicyon
Group=epicyon
WorkingDirectory=/opt/epicyon
ExecStart=/usr/bin/python3 /opt/epicyon/epicyon.py --port 443 --proxy 7156 --domain YOUR_DOMAIN --registration open
Environment=USER=epicyon
Environment=PYTHONUNBUFFERED=true
Restart=always
StandardError=syslog

[Install]
WantedBy=multi-user.target
```

Here the server was installed to */opt/epicyon*, but you can change that to wherever you installed it.

Then run the daemon:

``` bash
systemctl enable epicyon
chown -R epicyon:epicyon /opt/epicyon
systemctl start epicyon
```

Check the status of the daemon with:

``` bash
systemctl status epicyon
```

If it's not running then you can also look at the log:

``` bash
journalctl -u epicyon
```

You'll also need to set up a web server configuration. For Nginx edit */etc/nginx/sites-available/YOUR_DOMAIN* as follows:

``` nginx
server {
    listen 80;
    listen [::]:80;
    server_name YOUR_DOMAIN;
    access_log /dev/null;
    error_log /dev/null;
    client_max_body_size 31m;
    client_body_buffer_size 128k;

    index index.html;
    rewrite ^ https://$server_name$request_uri? permanent;
}

server {
    listen 443 ssl;
    server_name YOUR_DOMAIN;

    ssl_stapling off;
    ssl_stapling_verify off;
    ssl on;
    ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem;
    #ssl_dhparam /etc/ssl/certs/YOUR_DOMAIN.dhparam;

    ssl_session_cache  builtin:1000  shared:SSL:10m;
    ssl_session_timeout 60m;
    ssl_prefer_server_ciphers on;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-RSA-AES256-SHA:ECDHE-ECDSA-DES-CBC3-SHA:ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:!DSS';
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header X-Download-Options noopen;
    add_header X-Permitted-Cross-Domain-Policies none;

    add_header X-Robots-Tag "noindex, nofollow, nosnippet, noarchive";
    add_header Strict-Transport-Security max-age=15768000;

    access_log /dev/null;
    error_log /dev/null;

    index index.html;
 
    location / {
        proxy_http_version 1.1;
        client_max_body_size 31M;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forward-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forward-Proto http;
        proxy_set_header X-Nginx-Proxy true;
        proxy_temp_file_write_size 64k;
        proxy_connect_timeout 10080s;
        proxy_send_timeout 10080;
        proxy_read_timeout 10080;
        proxy_buffer_size 64k;
        proxy_buffers 16 32k;
        proxy_busy_buffers_size 64k;
        proxy_redirect off;
        proxy_request_buffering on;
        proxy_buffering on;
        proxy_pass http://localhost:7156;
    }
}
```

Changing your domain name as appropriate. Activate the configuration with:

``` bash
ln -s /etc/nginx/sites-available/YOUR_DOMAIN /etc/nginx/sites-enabled/
```

Generate a LetsEncrypt certificate.

``` bash
certbot certonly -n --server https://acme-v01.api.letsencrypt.org/directory --standalone -d YOUR_DOMAIN --renew-by-default --agree-tos --email YOUR_EMAIL
```

And restart the web server:

``` bash
systemctl restart nginx
```

If you are using the [Caddy web server](https://caddyserver.com) then see *caddy.example.conf*

## Running Static Analysis

Static analysis can be run with:

``` bash
./static_analysis
```

## Installing on Onion or i2p domains

If you don't have access to the clearnet, or prefer not to use it, then it's possible to run an Epicyon instance easily from your laptop. There are scripts within the ```deploy``` directory which can be used to install an instance on a Debian or Arch/Parabola operating system. With some modification of package names they could be also used with other distros.

Please be aware that such installations will not federate with ordinary fediverse instances on the clearnet, unless those instances have been specially modified to do so. But onion instances will federate with other onion instances and i2p instances with other i2p instances.


## Custom Fonts

If you want to use a particular font then copy it into the *fonts* directory, rename it as *custom.ttf/woff/woff2/otf* and then restart the epicyon daemon.

``` bash
systemctl restart epicyon
```

## Custom Favicon

If you want to use your own favicon then copy your `favicon.ico` file to the base directory where you installed Epicyon.


## Adding Themes

If you want to add a new theme then open `theme.py` and add the theme name to the list within `getThemesList`. Add a function with the name `setTheme[YourThemeName]`. Have a look at the other themes to get an idea of how to set the colors and fonts.

Add the name of your theme to the translations files.

Within the `img` directory add a default profile background image called `image_[YourThemeName].png` and a banner image `banner_[YourThemeName].png`. Because the banner image will be reloaded occasionally it should be small - preferably kilobytes rather than megabytes.

On a running instance you can experiment with colors or fonts by editing `epicyon.css` and then reloading the web page. Once you are happy with the results then you can update the changed values within your `setTheme` function.


## Running Unit Tests

To run the unit tests:

``` bash
python3 epicyon.py --tests
```

To run the network tests. These simulate instances exchanging messages.

``` bash
python3 epicyon.py --testsnetwork
```

