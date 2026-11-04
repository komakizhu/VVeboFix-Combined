#import "NoRefreshPolicy.h"

static NSObject *XHSNoRefreshLock;
static BOOL XHSNoRefreshEnabled = YES;
static BOOL XHSNoRefreshActivationActive;
static BOOL XHSNoRefreshUserInteracted;
static NSTimeInterval XHSNoRefreshActivationDeadline;
// Zero means keep protecting the activation until the user interacts.
static NSTimeInterval XHSNoRefreshActivationWindow;

static void XHSNoRefreshEnsureLock(void) {
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        XHSNoRefreshLock = [NSObject new];
    });
}

static NSString *XHSNoRefreshQueryValue(NSURLRequest *request, NSString *name) {
    NSURLComponents *components = [NSURLComponents componentsWithURL:request.URL
                                               resolvingAgainstBaseURL:NO];
    for (NSURLQueryItem *item in components.queryItems) {
        if ([item.name caseInsensitiveCompare:name] == NSOrderedSame) {
            return item.value;
        }
    }
    return nil;
}

static NSInteger XHSNoRefreshIntegerValue(NSString *value) {
    if (value.length == 0) return 0;
    NSScanner *scanner = [NSScanner scannerWithString:value];
    NSInteger number = 0;
    if (![scanner scanInteger:&number] || !scanner.isAtEnd) return 0;
    return number;
}

static BOOL XHSNoRefreshCursorIsPresent(NSString *value) {
    return value.length > 0 && ![value isEqualToString:@"0"];
}

static NSDictionary *XHSNoRefreshJSONBody(NSURLRequest *request) {
    NSData *body = request.HTTPBody;
    if (body.length == 0) return nil;
    id object = [NSJSONSerialization JSONObjectWithData:body options:0 error:NULL];
    return [object isKindOfClass:NSDictionary.class] ? object : nil;
}

static BOOL XHSNoRefreshBodyHasCursor(NSDictionary *body) {
    id cursor = body[@"cursor_score"] ?: body[@"cursor"];
    if ([cursor isKindOfClass:NSString.class] && XHSNoRefreshCursorIsPresent(cursor)) {
        return YES;
    }
    id noteIndex = body[@"note_index"];
    if ([noteIndex respondsToSelector:@selector(integerValue)] &&
        [noteIndex integerValue] > 0) {
        return YES;
    }
    return NO;
}

static BOOL XHSNoRefreshQueryHasCursor(NSURLRequest *request) {
    NSString *cursor = XHSNoRefreshQueryValue(request, @"cursor_score");
    if (!cursor) cursor = XHSNoRefreshQueryValue(request, @"cursor");
    if (XHSNoRefreshCursorIsPresent(cursor)) return YES;
    NSString *noteIndex = XHSNoRefreshQueryValue(request, @"note_index");
    return XHSNoRefreshIntegerValue(noteIndex) > 0;
}

static NSString *XHSNoRefreshRefreshType(NSURLRequest *request) {
    NSString *refreshType = XHSNoRefreshQueryValue(request, @"refresh_type");
    if (refreshType) return refreshType;
    NSDictionary *body = XHSNoRefreshJSONBody(request);
    id value = body[@"refresh_type"];
    return [value respondsToSelector:@selector(stringValue)] ? [value stringValue] : nil;
}

static BOOL XHSNoRefreshHasExplicitRefreshType(NSURLRequest *request) {
    return XHSNoRefreshRefreshType(request) != nil;
}

void XHSNoRefreshBeginActivation(NSTimeInterval now) {
    XHSNoRefreshEnsureLock();
    @synchronized (XHSNoRefreshLock) {
        XHSNoRefreshActivationActive = YES;
        XHSNoRefreshUserInteracted = NO;
        XHSNoRefreshActivationDeadline = XHSNoRefreshActivationWindow > 0.0
            ? now + XHSNoRefreshActivationWindow
            : 0.0;
    }
}

void XHSNoRefreshMarkUserInteraction(void) {
    XHSNoRefreshEnsureLock();
    @synchronized (XHSNoRefreshLock) {
        XHSNoRefreshUserInteracted = YES;
    }
}

void XHSNoRefreshSetEnabled(BOOL enabled) {
    XHSNoRefreshEnsureLock();
    @synchronized (XHSNoRefreshLock) {
        XHSNoRefreshEnabled = enabled;
    }
}

BOOL XHSNoRefreshIsEnabled(void) {
    XHSNoRefreshEnsureLock();
    @synchronized (XHSNoRefreshLock) {
        return XHSNoRefreshEnabled;
    }
}

void XHSNoRefreshSetWindow(NSTimeInterval seconds) {
    if (seconds < 0.0) seconds = 0.0;
    if (seconds > 60.0) seconds = 60.0;
    XHSNoRefreshEnsureLock();
    @synchronized (XHSNoRefreshLock) {
        XHSNoRefreshActivationWindow = seconds;
    }
}

NSTimeInterval XHSNoRefreshWindow(void) {
    XHSNoRefreshEnsureLock();
    @synchronized (XHSNoRefreshLock) {
        return XHSNoRefreshActivationWindow;
    }
}

BOOL XHSNoRefreshIsHomeFeedRequest(NSURLRequest *request) {
    NSURL *URL = request.URL;
    NSString *host = URL.host.lowercaseString;
    if (![host isEqualToString:@"xiaohongshu.com"] &&
        ![host hasSuffix:@".xiaohongshu.com"]) {
        return NO;
    }
    NSString *path = URL.path.lowercaseString;
    return [path hasSuffix:@"/homefeed"] || [path hasSuffix:@"/homefeed/"];
}

BOOL XHSNoRefreshIsInitialFeedRequest(NSURLRequest *request) {
    if (XHSNoRefreshQueryHasCursor(request)) return NO;
    NSDictionary *body = XHSNoRefreshJSONBody(request);
    if (body && XHSNoRefreshBodyHasCursor(body)) return NO;
    return YES;
}

BOOL XHSNoRefreshIsAutomaticRefreshRequest(NSURLRequest *request) {
    NSString *refreshType = XHSNoRefreshRefreshType(request);
    NSString *path = request.URL.path.lowercaseString;
    BOOL legacyIOS = [path hasSuffix:@"/api/sns/v6/homefeed"] ||
                     [path hasSuffix:@"/api/sns/v6/homefeed/"];
    BOOL webStyle = [path hasSuffix:@"/api/sns/web/v1/homefeed"] ||
                    [path hasSuffix:@"/api/sns/web/v1/homefeed/"];
    // Public iOS captures use 2; web-style clients commonly use 1. Keep the
    // match endpoint-specific so an unknown marker is never treated as an
    // automatic refresh by guesswork.
    if (legacyIOS) return [refreshType isEqualToString:@"2"];
    if (webStyle) return [refreshType isEqualToString:@"1"];
    return NO;
}

BOOL XHSNoRefreshShouldBlockRequest(NSURLRequest *request, NSTimeInterval now) {
    if (!XHSNoRefreshIsHomeFeedRequest(request) ||
        !XHSNoRefreshIsInitialFeedRequest(request)) {
        return NO;
    }
    XHSNoRefreshEnsureLock();
    @synchronized (XHSNoRefreshLock) {
        if (!XHSNoRefreshEnabled || !XHSNoRefreshActivationActive ||
            XHSNoRefreshUserInteracted ||
            (XHSNoRefreshActivationDeadline > 0.0 &&
             now > XHSNoRefreshActivationDeadline)) {
            return NO;
        }
    }
    // Only block a request when the endpoint and marker identify the known
    // automatic-refresh path. Unknown or unmarked requests stay untouched.
    return XHSNoRefreshIsAutomaticRefreshRequest(request) &&
           XHSNoRefreshHasExplicitRefreshType(request);
}
