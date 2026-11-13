export function formatDateTime(isoUtc, timeZone) {
  const options = {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  };
  if (timeZone !== undefined) {
    options.timeZone = timeZone;
  }
  const formatter = new Intl.DateTimeFormat("en-GB", options);
  const parts = {};
  for (const { type, value } of formatter.formatToParts(new Date(isoUtc))) {
    parts[type] = value;
  }
  return `${parts.day}/${parts.month}/${parts.year} ${parts.hour}:${parts.minute}`;
}
