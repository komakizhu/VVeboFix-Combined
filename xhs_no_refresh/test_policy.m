#import <Foundation/Foundation.h>
#include <stdio.h>
#include <stdlib.h>
#import "NoRefreshPolicy.h"

static void Check(BOOL condition, NSString *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message.UTF8String);
        exit(1);
    }
    printf("PASS: %s\n", message.UTF8String);
}

static NSMutableURLRequest *Request(NSString *URLString) {
    return [NSMutableURLRequest requestWithURL:[NSURL URLWithString:URLString]];
}

int main(void) {
    @autoreleasepool {
        XHSNoRefreshSetEnabled(YES);
        XHSNoRefreshSetWindow(8.0);
        XHSNoRefreshBeginActivation(100.0);

        NSURLRequest *automatic = Request(
            @"https://edith.xiaohongshu.com/api/sns/v6/homefeed?oid=homefeed_recommend&refresh_type=2");
        Check(XHSNoRefreshIsHomeFeedRequest(automatic),
              @"Recognizes the iOS homefeed endpoint");
        Check(XHSNoRefreshIsInitialFeedRequest(automatic),
              @"Recognizes an initial homefeed request");
        Check(XHSNoRefreshIsAutomaticRefreshRequest(automatic),
              @"Recognizes the app's automatic refresh marker");
        Check(XHSNoRefreshShouldBlockRequest(automatic, 101.0),
              @"Blocks startup homefeed refresh before interaction");

        NSURLRequest *nextPage = Request(
            @"https://edith.xiaohongshu.com/api/sns/v6/homefeed?cursor_score=next&refresh_type=2");
        Check(!XHSNoRefreshIsInitialFeedRequest(nextPage),
              @"Recognizes a paginated homefeed request");
        Check(!XHSNoRefreshShouldBlockRequest(nextPage, 101.0),
              @"Leaves pagination available");

        NSMutableURLRequest *webInitial = Request(
            @"https://edith.xiaohongshu.com/api/sns/web/v1/homefeed");
        webInitial.HTTPMethod = @"POST";
        webInitial.HTTPBody = [NSJSONSerialization dataWithJSONObject:@{
            @"cursor_score": @"",
            @"note_index": @0,
            @"refresh_type": @1,
            @"category": @"homefeed_recommend"
        } options:0 error:NULL];
        Check(XHSNoRefreshIsHomeFeedRequest(webInitial),
              @"Recognizes the newer web-style homefeed endpoint");
        Check(XHSNoRefreshShouldBlockRequest(webInitial, 101.0),
              @"Blocks the web-style automatic refresh marker");

        NSMutableURLRequest *unknownMarker = Request(
            @"https://edith.xiaohongshu.com/api/sns/web/v1/homefeed");
        unknownMarker.HTTPMethod = @"POST";
        unknownMarker.HTTPBody = [NSJSONSerialization dataWithJSONObject:@{
            @"cursor_score": @"",
            @"note_index": @0,
            @"refresh_type": @0
        } options:0 error:NULL];
        Check(!XHSNoRefreshShouldBlockRequest(unknownMarker, 101.0),
              @"Leaves explicitly non-automatic refresh types available");

        NSURLRequest *unmarked = Request(
            @"https://edith.xiaohongshu.com/api/sns/v6/homefeed?oid=homefeed_recommend");
        Check(!XHSNoRefreshShouldBlockRequest(unmarked, 101.0),
              @"Leaves unmarked requests untouched");

        NSURLRequest *unknownEndpoint = Request(
            @"https://edith.xiaohongshu.com/api/sns/v9/homefeed?refresh_type=2");
        Check(!XHSNoRefreshShouldBlockRequest(unknownEndpoint, 101.0),
              @"Leaves unknown homefeed endpoints untouched");

        XHSNoRefreshMarkUserInteraction();
        Check(!XHSNoRefreshShouldBlockRequest(automatic, 101.0),
              @"Allows refresh after user interaction");

        XHSNoRefreshBeginActivation(200.0);
        Check(!XHSNoRefreshShouldBlockRequest(automatic, 209.0),
              @"Stops blocking after an optional activation window");

        XHSNoRefreshBeginActivation(300.0);
        XHSNoRefreshSetWindow(0.0);
        XHSNoRefreshBeginActivation(300.0);
        Check(XHSNoRefreshShouldBlockRequest(automatic, 3300.0),
              @"Keeps blocking indefinitely until interaction by default");
        XHSNoRefreshSetEnabled(NO);
        Check(!XHSNoRefreshShouldBlockRequest(automatic, 301.0),
              @"Supports a runtime disable switch");

        XHSNoRefreshSetEnabled(YES);
        XHSNoRefreshBeginActivation(400.0);
        NSURLRequest *unrelated = Request(
            @"https://edith.xiaohongshu.com/api/sns/v6/user/info?user_id=123");
        Check(!XHSNoRefreshIsHomeFeedRequest(unrelated),
              @"Does not classify unrelated API requests as homefeed");
        Check(!XHSNoRefreshShouldBlockRequest(unrelated, 401.0),
              @"Leaves unrelated API requests untouched");

        NSURLRequest *otherHost = Request(
            @"https://evil-xiaohongshu.com/api/sns/v6/homefeed?refresh_type=2");
        Check(!XHSNoRefreshIsHomeFeedRequest(otherHost),
              @"Rejects lookalike hosts");
    }
    return 0;
}
