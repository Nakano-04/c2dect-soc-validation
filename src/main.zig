const std = @import("std");

var global_io: std.Io = undefined;

const Event = struct {
    session: []const u8,
    technique: []const u8,
    t: f64,
    contained_t: ?f64 = null,
    true_positive: bool = false,
};

fn out(allocator: std.mem.Allocator, comptime fmt: []const u8, args: anytype) !void {
    const text = try std.fmt.allocPrint(allocator, fmt, args);
    defer allocator.free(text);
    try std.Io.File.stdout().writeStreamingAll(global_io, text);
}

fn parseEvent(allocator: std.mem.Allocator, line: []const u8) !Event {
    const parsed = try std.json.parseFromSlice(std.json.Value, allocator, line, .{});
    defer parsed.deinit();
    const obj = parsed.value.object;
    const session_val = obj.get("session") orelse return error.MissingField;
    const tech_val = obj.get("technique") orelse return error.MissingField;
    const t_val = obj.get("t") orelse return error.MissingField;

    var contained: ?f64 = null;
    if (obj.get("contained_t")) |v| {
        if (v == .float) contained = v.float else if (v == .integer) contained = @floatFromInt(v.integer);
    }
    var tp = false;
    if (obj.get("true_positive")) |v| {
        if (v == .bool) tp = v.bool;
    }

    return .{
        .session = try allocator.dupe(u8, session_val.string),
        .technique = try allocator.dupe(u8, tech_val.string),
        .t = if (t_val == .float) t_val.float else @floatFromInt(t_val.integer),
        .contained_t = contained,
        .true_positive = tp,
    };
}

fn loadEvents(allocator: std.mem.Allocator, path: []const u8) !std.ArrayList(Event) {
    const data = try std.Io.Dir.cwd().readFileAlloc(global_io, path, allocator, std.Io.Limit.limited(16 * 1024 * 1024));
    defer allocator.free(data);
    var list: std.ArrayList(Event) = .empty;
    var lines = std.mem.splitScalar(u8, data, '\n');
    while (lines.next()) |raw| {
        const line = std.mem.trim(u8, raw, " \t\r");
        if (line.len == 0) continue;
        try list.append(allocator, try parseEvent(allocator, line));
    }
    return list;
}

pub fn main(init: std.process.Init) !void {
    const allocator = init.arena.allocator();
    global_io = init.io;
    const args = try init.minimal.args.toSlice(allocator);
    if (args.len < 3) {
        try out(allocator, "uso: tt_calc_zig <executions.jsonl> <alerts.jsonl>\n", .{});
        std.process.exit(2);
    }

    var executions = try loadEvents(allocator, args[1]);
    defer executions.deinit(allocator);
    var alerts = try loadEvents(allocator, args[2]);
    defer alerts.deinit(allocator);

    var detected: usize = 0;
    var contained: usize = 0;
    var sum_ttd: f64 = 0;
    var sum_ttc: f64 = 0;

    for (executions.items) |ex| {
        var best_ttd: ?f64 = null;
        var best_ttc: ?f64 = null;
        for (alerts.items) |al| {
            if (!std.mem.eql(u8, al.session, ex.session)) continue;
            if (!std.mem.eql(u8, al.technique, ex.technique)) continue;
            if (al.t < ex.t) continue;
            const ttd = al.t - ex.t;
            if (best_ttd == null or ttd < best_ttd.?) best_ttd = ttd;
            if (al.contained_t) |ct| {
                if (ct >= ex.t and ct >= al.t) {
                    const ttc = ct - ex.t;
                    if (best_ttc == null or ttc < best_ttc.?) best_ttc = ttc;
                }
            }
        }
        if (best_ttd) |v| {
            detected += 1;
            sum_ttd += v;
        }
        if (best_ttc) |v| {
            contained += 1;
            sum_ttc += v;
        }
    }

    var tp: usize = 0;
    for (alerts.items) |al| if (al.true_positive) { tp += 1; };

    const mean_ttd: f64 = if (detected > 0) sum_ttd / @as(f64, @floatFromInt(detected)) else 0;
    const mean_ttc: f64 = if (contained > 0) sum_ttc / @as(f64, @floatFromInt(contained)) else 0;
    const recall: f64 = if (executions.items.len > 0)
        @as(f64, @floatFromInt(detected)) / @as(f64, @floatFromInt(executions.items.len))
    else
        0;
    const precision: f64 = if (alerts.items.len > 0)
        @as(f64, @floatFromInt(tp)) / @as(f64, @floatFromInt(alerts.items.len))
    else
        0;

    try out(allocator,
        "{{\"executions\":{d},\"detected\":{d},\"contained\":{d},\"recall\":{d:.4},\"precision\":{d:.4},\"mean_ttd\":{d:.4},\"mean_ttc\":{d:.4}}}\n",
        .{ executions.items.len, detected, contained, recall, precision, mean_ttd, mean_ttc },
    );
}

test "parseEvent lee contained_t" {
    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const e = try parseEvent(gpa.allocator(), "{\"session\":\"s1\",\"technique\":\"T1\",\"t\":1.0,\"contained_t\":4.0,\"true_positive\":true}");
    defer gpa.allocator().free(e.session);
    defer gpa.allocator().free(e.technique);
    try std.testing.expectEqual(@as(f64, 4.0), e.contained_t.?);
    try std.testing.expect(e.true_positive);
}
