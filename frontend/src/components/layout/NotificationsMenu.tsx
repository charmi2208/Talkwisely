"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { formatDistanceToNow } from "date-fns";
import { AlertCircle, Bell, CheckCircle, TrendingUp } from "lucide-react";
import { notificationsApi, type AppNotification } from "@/lib/api/notifications";
import { parseApiDate } from "@/lib/dates";
import { Button } from "@/components/ui/button";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Item, ItemContent, ItemDescription, ItemGroup, ItemMedia, ItemTitle } from "@/components/ui/item";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";

const REFRESH_MS = 60_000;

const typeIcon: Record<string, React.ElementType> = {
  processing_complete: CheckCircle,
  processing_failed: AlertCircle,
  high_intent_lead: TrendingUp,
};

export function NotificationsMenu() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<AppNotification[]>([]);

  const load = useCallback(async () => {
    try {
      setItems(await notificationsApi.list());
    } catch {
      // Keep the last known list; the bell stays usable if a refresh fails
    }
  }, []);

  useEffect(() => {
    notificationsApi.list().then(setItems).catch(() => {});
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
  }, [load]);

  const unreadCount = items.filter((n) => !n.is_read).length;

  const handleSelect = async (n: AppNotification) => {
    setOpen(false);
    if (!n.is_read) {
      setItems((prev) => prev.map((i) => (i.id === n.id ? { ...i, is_read: true } : i)));
      notificationsApi.markRead(n.id).catch(() => load());
    }
    if (n.conversation_id) router.push(`/conversations/${n.conversation_id}`);
  };

  const handleMarkAll = async () => {
    setItems((prev) => prev.map((i) => ({ ...i, is_read: true })));
    try {
      await notificationsApi.markAllRead();
    } catch {
      load();
    }
  };

  return (
    <Popover open={open} onOpenChange={(o) => { setOpen(o); if (o) load(); }}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="relative"
          aria-label={unreadCount ? `Notifications, ${unreadCount} unread` : "Notifications"}
        >
          <Bell />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 flex min-w-4 h-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold text-primary-foreground tabular-nums">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-96 p-0">
        <div className="flex items-center justify-between px-4 py-3">
          <p className="text-sm font-semibold">Notifications</p>
          <Button variant="ghost" size="xs" onClick={handleMarkAll} disabled={unreadCount === 0}>
            Mark all as read
          </Button>
        </div>
        <Separator />
        {items.length === 0 ? (
          <Empty className="p-8">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <Bell />
              </EmptyMedia>
              <EmptyTitle className="text-sm">You&apos;re all caught up</EmptyTitle>
              <EmptyDescription className="text-xs">
                You&apos;ll be notified when a recording finishes processing.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : (
          <ScrollArea className="*:data-[slot=scroll-area-viewport]:max-h-96">
            <ItemGroup className="gap-0 p-1">
              {items.map((n) => {
                const Icon = typeIcon[n.type] ?? Bell;
                return (
                  <Item key={n.id} size="sm" asChild className={n.is_read ? "opacity-70 hover:bg-muted" : "hover:bg-muted"}>
                    <button type="button" onClick={() => handleSelect(n)} className="text-left">
                      <ItemMedia variant="icon">
                        <Icon className={n.type === "processing_failed" ? "text-destructive" : "text-muted-foreground"} />
                      </ItemMedia>
                      <ItemContent className="min-w-0">
                        <ItemTitle className="w-full">
                          <span className="truncate">{n.title}</span>
                          {!n.is_read && <span className="ml-auto size-2 shrink-0 rounded-full bg-primary" aria-label="Unread" />}
                        </ItemTitle>
                        <ItemDescription className="text-xs">{n.message}</ItemDescription>
                        <span className="text-[11px] text-muted-foreground">
                          {formatDistanceToNow(parseApiDate(n.created_at), { addSuffix: true })}
                        </span>
                      </ItemContent>
                    </button>
                  </Item>
                );
              })}
            </ItemGroup>
          </ScrollArea>
        )}
      </PopoverContent>
    </Popover>
  );
}
