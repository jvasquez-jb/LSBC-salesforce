"""Portal look: writes the LSBC LPI theme, branding set and home page from scripts/generators/portal/.

    python3 -I scripts/generators/portaltheme.py

Sources (edit these, not the JSON):
  portal/theme.css    the theme's custom CSS (fonts, masthead, hero, home sections, footer, inner pages, login)
  portal/footer.html  the site footer, on every page layout that has one
  portal/home.html    the home page body under the hero

The script also sets the header, profile button, header search and hero attributes, and the branding set colours,
fonts and logo. Then deploy force-app/main/default/experiences/LSBC_LPI1 and the Portal* static resources, and publish
the site (sf community publish --name "LSBC LPI").
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITE = os.path.join(ROOT, 'force-app/main/default/experiences/LSBC_LPI1')
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'portal')

INK, NAVY = '#111111', '#091580'
PAGE, SLATE = '#D3DCE8', '#4A4D78'  # the Board's pale cool blue-grey and cool slate blue (19 Nov 2026)

HEADER = {  # forceCommunity:themeHeaderStacked, on every layout
    'background': 'background: ' + PAGE,
    'backgroundOverlayColor': 'rgba(0, 0, 0, 0)',
    'borderBottomColor': INK,
    'borderTopColor': 'rgba(0, 0, 0, 0)',
    'bottomRowOverlayColor': 'rgba(0, 0, 0, 0)',
    'dropdownBackgroundColor': '#FFFFFF',
    'dropdownBackgroundHoverColor': '#F2F2F2',
    'dropdownBorderColor': INK,
    'dropdownTextColor': INK,
    'dropdownTextHoverColor': INK,
    'iconLinkColor': INK,
    'iconLinkHoverColor': NAVY,
    'iconLinkTextShadowColor': '',
    'linkActiveBorderColor': INK,
    'linkColor': INK,
    'linkHoverColor': INK,
    'linkTextShadowColor': 'rgba(0, 0, 0, 0)',
    'logoWidth': 250,  # Salesforce maximum; theme.css sets the displayed size
}
PROFILE_MENU_STYLE = ('{"selectedMenuStyleSetting":"iconOnly","selectedIconSetting":"userAvatar",'
                      '"includeCompanyName":false,"selectedTextOrientationSetting":"right"}')
PROFILE = {  # forceCommunity:customizableUserProfileMenu (the Log in button and the signed-in menu)
    'buttonBackgroundColor': INK,
    'buttonBackgroundHoverColor': NAVY,
    'buttonBorderColor': INK,
    'buttonBorderRadius': 0,
    'buttonTextColor': '#FFFFFF',
    'buttonTextHoverColor': '#FFFFFF',
}
SEARCH = {  # forceCommunity:themeSearch in the header of inner pages
    'backgroundColor': '#FFFFFF',
    'borderColor': INK,
    'borderRadius': 0,
    'iconColor': INK,
    'placeholderTextColor': '#5A5A5A',
    'textColor': INK,
}
HERO = {  # forceCommunity:themeHeroStarter on the home layout
    'bgImage': 'background: #0E0E0E',
    'bgOverlayColor': 'rgba(0, 0, 0, 0)',
    'subtitleTextColor': PAGE,
    'titleTextColor': '#FFFFFF',
    'titleText': 'How can we help?',
}
SEARCH_HERO = {  # forceCommunity:themeSearchHero, the search box in the home hero: white, square, no border
    'backgroundColor': '#FFFFFF',
    'borderColor': '#FFFFFF',
    'borderRadius': 0,
    'iconColor': INK,
    'textColor': INK,
    'placeholderTextColor': '#5A5A5A',
}
NAV = {'navAlignment': 'center'}
BRANDING = {
    'ActionColor': INK,
    '_ActionColorDarker': '#000000',
    '_ActionColorTrans': 'rgba(17, 17, 17, 0.9)',
    'BorderColor': '#8A8A8A',
    'CompanyLogo': '/sfsites/c/resource/PortalLogoNavy',
    'DetailTextColor': '#5A5A5A',
    'HeaderFonts': 'Montserrat',
    'PrimaryFont': 'Montserrat',
    'LinkColor': NAVY,
    '_LinkColorDarker': '#060E57',
    'LoginBackgroundColor': '#000000',
    'TextColor': INK,
    '_DxpPageBackgroundColor': PAGE,
    '_HoverColor': 'rgba(0, 0, 0, 0.04)',
    '_PrimaryAccentColor1': INK,
    '_PrimaryAccentColor2': '#000000',
}


def read(name):
    with open(os.path.join(SRC, name), encoding='utf-8') as f:
        return f.read().strip()


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save(path, data, seps=(',', ': ')):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, indent=2, separators=seps, ensure_ascii=True))


def components(node):
    """Every component in a view, at any depth."""
    for region in node.get('regions', []) or []:
        for comp in region.get('components', []) or []:
            yield region['regionName'], comp
            yield from components(comp)


def theme():
    path = os.path.join(SITE, 'themes/licensePermits.json')
    t = load(path)
    t['customCSS'] = read('theme.css') + '\n'
    footer = read('footer.html')
    for view in t['views']:
        if view['componentName'] == 'siteforce:lpiLayoutStarter':
            view['componentAttributes']['isHeroUnderHeader'] = False  # white masthead above the black hero
        for region, comp in components(view):
            name, attrs = comp['componentName'], comp.setdefault('componentAttributes', {})
            if name == 'forceCommunity:themeHeaderStacked':
                attrs.update(HEADER)
            elif name in ('forceCommunity:themeProfileMenu', 'forceCommunity:customizableUserProfileMenu'):
                # The customizable menu reads its items (My School, My Businesses) from Default_User_Profile_Menu;
                # the theme's own profile menu ignores that navigation menu.
                comp['componentName'] = 'forceCommunity:customizableUserProfileMenu'
                comp['componentAttributes'] = dict(PROFILE, buttonText='Log in',
                                                   customizableUserProfileMenuEditor='Default_User_Profile_Menu',
                                                   menuStyleSettings=PROFILE_MENU_STYLE)
            elif name == 'forceCommunity:themeSearch':
                attrs.update(SEARCH)
            elif name == 'forceCommunity:themeSearchHero':
                attrs.update(SEARCH_HERO)
            elif name == 'forceCommunity:themeHeroStarter':
                attrs.update(HERO)
            elif name == 'forceCommunity:themeNav':
                attrs.update(NAV)
            elif name == 'forceCommunity:htmlBlock' and region == 'themeFooter':
                attrs['richTextValue'] = footer
    save(path, t)


def branding():
    path = os.path.join(SITE, 'brandingSets/licensePermits.json')
    b = load(path)
    b['values'].update(BRANDING)
    save(path, b)


BLOCK_IDS = ('83076612-e9a9-442a-bcb4-a66b2fa20e20', '1aaa3c58-0373-4185-9025-eaa24288eff4')
MARKER = '<!-- COLLECTION'


def html_block(cid, html):
    return {'componentAttributes': {'richTextValue': html}, 'componentName': 'forceCommunity:htmlBlock', 'id': cid,
            'renderPriority': 'NEUTRAL', 'renditionMap': {}, 'type': 'component'}


def home():
    """Under the hero: the first HTML block (topics, promo, news heading), the Board News & Publications CMS
    collection (portal/news_collection.json, made in Experience Builder and kept here), then the second HTML block
    (popular tasks, help). Any other collection or HTML block on the page is removed."""
    path = os.path.join(SITE, 'views/home.json')
    v = load(path)
    first, second = read('home.html').split(MARKER, 1)
    second = second.split('-->', 1)[1].strip()
    with open(os.path.join(SRC, 'news_collection.json'), encoding='utf-8') as f:
        collection = json.load(f)
    managed = ('forceCommunity:htmlBlock', 'forceCommunity:dynamicCollection')
    for region in v['regions']:
        region_components = region.get('components')
        if region_components is None:
            continue
        others = [c for c in region_components if c['componentName'] not in managed]
        if region['regionName'] == 'footer':
            region['components'] = [html_block(BLOCK_IDS[0], first.strip()),
                                    collection, html_block(BLOCK_IDS[1], second)] + others
        else:
            region['components'] = others
    save(path, v, seps=(',', ' : '))


if __name__ == '__main__':
    theme()
    branding()
    home()
    print('Portal theme, branding set and home page written.')
