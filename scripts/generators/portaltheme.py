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

INK, NAVY, GOLD = '#111111', '#091580', '#C9A44A'

HEADER = {  # forceCommunity:themeHeaderStacked, on every layout
    'background': 'background: #FFFFFF',
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
PROFILE = {  # forceCommunity:themeProfileMenu (the Log in button)
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
    'subtitleTextColor': GOLD,
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
    '_DxpPageBackgroundColor': '#FFFFFF',
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
            elif name == 'forceCommunity:themeProfileMenu':
                attrs.update(PROFILE)
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


def home():
    """One HTML block under the hero, replacing the earlier three."""
    path = os.path.join(SITE, 'views/home.json')
    v = load(path)
    for region in v['regions']:
        blocks = [c for c in region.get('components', []) if c['componentName'] == 'forceCommunity:htmlBlock']
        if not blocks:
            continue
        keep = blocks[0]
        keep['componentAttributes']['richTextValue'] = read('home.html')
        region['components'] = [c for c in region['components'] if c is keep or c not in blocks]
    save(path, v, seps=(',', ' : '))


if __name__ == '__main__':
    theme()
    branding()
    home()
    print('Portal theme, branding set and home page written.')
