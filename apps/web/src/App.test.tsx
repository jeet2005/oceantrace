import { describe, expect, it } from "vitest";
import { renderToString } from "react-dom/server";
import { App } from "./App";

describe("App", () => {
  it("renders the product workspace", () => {
    const html = renderToString(<App />);

    expect(html).toContain("OCEANTRACE");
    expect(html).toContain("not definitive attribution");
  });
});
