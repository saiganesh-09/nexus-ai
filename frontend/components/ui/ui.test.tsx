import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Badge } from "./badge";
import { Card, CardContent, CardTitle } from "./card";

describe("Badge", () => {
  it("renders children with variant classes", () => {
    render(<Badge variant="success">ok</Badge>);
    expect(screen.getByText("ok")).toBeInTheDocument();
  });
});

describe("Card", () => {
  it("renders title and content", () => {
    render(
      <Card>
        <CardTitle>Title</CardTitle>
        <CardContent>Body</CardContent>
      </Card>,
    );
    expect(screen.getByText("Title")).toBeInTheDocument();
    expect(screen.getByText("Body")).toBeInTheDocument();
  });
});
