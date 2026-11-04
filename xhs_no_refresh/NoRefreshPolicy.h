#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

FOUNDATION_EXPORT void XHSNoRefreshBeginActivation(NSTimeInterval now);
FOUNDATION_EXPORT void XHSNoRefreshMarkUserInteraction(void);
FOUNDATION_EXPORT void XHSNoRefreshSetEnabled(BOOL enabled);
FOUNDATION_EXPORT BOOL XHSNoRefreshIsEnabled(void);
FOUNDATION_EXPORT void XHSNoRefreshSetWindow(NSTimeInterval seconds);
FOUNDATION_EXPORT NSTimeInterval XHSNoRefreshWindow(void);

FOUNDATION_EXPORT BOOL XHSNoRefreshIsHomeFeedRequest(NSURLRequest *request);
FOUNDATION_EXPORT BOOL XHSNoRefreshIsInitialFeedRequest(NSURLRequest *request);
FOUNDATION_EXPORT BOOL XHSNoRefreshIsAutomaticRefreshRequest(NSURLRequest *request);
FOUNDATION_EXPORT BOOL XHSNoRefreshShouldBlockRequest(NSURLRequest *request,
                                                      NSTimeInterval now);

NS_ASSUME_NONNULL_END
