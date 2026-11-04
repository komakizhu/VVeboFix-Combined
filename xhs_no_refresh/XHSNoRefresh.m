#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>
#import <objc/runtime.h>
#import "NoRefreshPolicy.h"

@interface XHSNoRefreshURLProtocol : NSURLProtocol
@end

@implementation XHSNoRefreshURLProtocol

+ (BOOL)canInitWithRequest:(NSURLRequest *)request {
    return XHSNoRefreshShouldBlockRequest(request, NSDate.date.timeIntervalSince1970);
}

+ (NSURLRequest *)canonicalRequestForRequest:(NSURLRequest *)request {
    return request;
}

- (void)startLoading {
    NSError *error = [NSError errorWithDomain:NSURLErrorDomain
                                         code:NSURLErrorCancelled
                                     userInfo:@{
                                         NSLocalizedDescriptionKey:
                                             @"XHSNoRefresh suppressed the startup homefeed refresh"
                                     }];
    [self.client URLProtocol:self didFailWithError:error];
}

- (void)stopLoading {
}

@end

static IMP XHSOriginalSendEvent;
static IMP XHSOriginalDataTaskWithRequest;
static IMP XHSOriginalDataTaskWithURL;
static IMP XHSOriginalDataTaskWithRequestCompletion;
static IMP XHSOriginalDataTaskWithURLCompletion;

static BOOL XHSShouldBlockNow(NSURLRequest *request) {
    return XHSNoRefreshShouldBlockRequest(request, NSDate.date.timeIntervalSince1970);
}

static NSURLSessionDataTask *XHSCancelIfStartupRefresh(NSURLSessionDataTask *task,
                                                        NSURLRequest *request) {
    if (task && XHSShouldBlockNow(request)) {
        [task cancel];
    }
    return task;
}

static void XHSNoRefreshSendEvent(id self, SEL selector, UIEvent *event) {
    if (event.type == UIEventTypeTouches && event.allTouches.count > 0) {
        XHSNoRefreshMarkUserInteraction();
    }
    ((void (*)(id, SEL, UIEvent *))XHSOriginalSendEvent)(self, selector, event);
}

static NSURLSessionDataTask *XHSNoRefreshDataTaskWithRequest(id self,
                                                              SEL selector,
                                                              NSURLRequest *request) {
    NSURLSessionDataTask *task = ((NSURLSessionDataTask *(*)(id, SEL, NSURLRequest *))
                                      XHSOriginalDataTaskWithRequest)(self, selector, request);
    return XHSCancelIfStartupRefresh(task, request);
}

static NSURLSessionDataTask *XHSNoRefreshDataTaskWithURL(id self,
                                                         SEL selector,
                                                         NSURL *URL) {
    NSURLSessionDataTask *task = ((NSURLSessionDataTask *(*)(id, SEL, NSURL *))
                                      XHSOriginalDataTaskWithURL)(self, selector, URL);
    return XHSCancelIfStartupRefresh(task, [NSURLRequest requestWithURL:URL]);
}

static NSURLSessionDataTask *XHSNoRefreshDataTaskWithRequestCompletion(
    id self,
    SEL selector,
    NSURLRequest *request,
    void (^completionHandler)(NSData *, NSURLResponse *, NSError *)) {
    NSURLSessionDataTask *task = ((NSURLSessionDataTask *(*)(id, SEL, NSURLRequest *,
                                                              void (^)(NSData *, NSURLResponse *,
                                                                       NSError *)))
                                      XHSOriginalDataTaskWithRequestCompletion)(
        self, selector, request, completionHandler);
    return XHSCancelIfStartupRefresh(task, request);
}

static NSURLSessionDataTask *XHSNoRefreshDataTaskWithURLCompletion(
    id self,
    SEL selector,
    NSURL *URL,
    void (^completionHandler)(NSData *, NSURLResponse *, NSError *)) {
    NSURLSessionDataTask *task = ((NSURLSessionDataTask *(*)(id, SEL, NSURL *,
                                                              void (^)(NSData *, NSURLResponse *,
                                                                       NSError *)))
                                      XHSOriginalDataTaskWithURLCompletion)(
        self, selector, URL, completionHandler);
    return XHSCancelIfStartupRefresh(task, [NSURLRequest requestWithURL:URL]);
}

static void XHSInstallInstanceHook(Class cls, SEL selector, IMP replacement, IMP *original) {
    Method method = class_getInstanceMethod(cls, selector);
    if (!method || *original) return;
    *original = method_getImplementation(method);
    method_setImplementation(method, replacement);
}

static void XHSInstallHooks(void) {
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        [NSURLProtocol registerClass:XHSNoRefreshURLProtocol.class];

        XHSInstallInstanceHook(UIApplication.class, @selector(sendEvent:),
                               (IMP)XHSNoRefreshSendEvent, &XHSOriginalSendEvent);
        XHSInstallInstanceHook(NSURLSession.class, @selector(dataTaskWithRequest:),
                               (IMP)XHSNoRefreshDataTaskWithRequest,
                               &XHSOriginalDataTaskWithRequest);
        XHSInstallInstanceHook(NSURLSession.class, @selector(dataTaskWithURL:),
                               (IMP)XHSNoRefreshDataTaskWithURL,
                               &XHSOriginalDataTaskWithURL);
        XHSInstallInstanceHook(NSURLSession.class,
                               @selector(dataTaskWithRequest:completionHandler:),
                               (IMP)XHSNoRefreshDataTaskWithRequestCompletion,
                               &XHSOriginalDataTaskWithRequestCompletion);
        XHSInstallInstanceHook(NSURLSession.class, @selector(dataTaskWithURL:completionHandler:),
                               (IMP)XHSNoRefreshDataTaskWithURLCompletion,
                               &XHSOriginalDataTaskWithURLCompletion);
    });
}

static BOOL XHSNoRefreshTargetBundle(void) {
    NSString *identifier = NSBundle.mainBundle.bundleIdentifier;
    return [identifier isEqualToString:@"com.xingin.xhs"] ||
           [identifier isEqualToString:@"com.xingin.discover"];
}

static void XHSInstallLifecycleObservers(void) {
    NSNotificationCenter *center = NSNotificationCenter.defaultCenter;
    [center addObserverForName:UIApplicationWillEnterForegroundNotification
                        object:nil
                         queue:nil
                    usingBlock:^(NSNotification *note) {
                        (void)note;
                        XHSNoRefreshBeginActivation(NSDate.date.timeIntervalSince1970);
                    }];
    [center addObserverForName:UIApplicationDidBecomeActiveNotification
                        object:nil
                         queue:nil
                    usingBlock:^(NSNotification *note) {
                        (void)note;
                        XHSNoRefreshBeginActivation(NSDate.date.timeIntervalSince1970);
                    }];
}

__attribute__((constructor))
static void XHSNoRefreshLoad(void) {
    @autoreleasepool {
        if (!XHSNoRefreshTargetBundle()) return;

        NSNumber *disabled = [NSUserDefaults.standardUserDefaults
            objectForKey:@"XHSNoRefreshDisabled"];
        NSNumber *window = [NSUserDefaults.standardUserDefaults
            objectForKey:@"XHSNoRefreshWindow"];
        XHSNoRefreshSetEnabled(!disabled.boolValue);
        if (window) XHSNoRefreshSetWindow(window.doubleValue);
        XHSNoRefreshBeginActivation(NSDate.date.timeIntervalSince1970);
        XHSInstallLifecycleObservers();
        XHSInstallHooks();
        dispatch_async(dispatch_get_main_queue(), ^{
            XHSInstallHooks();
        });
        NSLog(@"[XHSNoRefresh] enabled=%@ window=%.2fs",
              XHSNoRefreshIsEnabled() ? @"YES" : @"NO", XHSNoRefreshWindow());
    }
}
