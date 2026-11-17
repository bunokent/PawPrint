import { describe, expect, it, vi } from "vitest";
import { useState } from "react";
import { http, HttpResponse } from "msw";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { PhotoUpload } from "@/features/pets/components/PhotoUpload";
import type { PhotoUploadResult } from "@/features/pets/api";
import { mswServer } from "@/test/setup";
import { renderWithProviders } from "@/test/utils";
import { setUploadRejects } from "@/test/handlers";

const uploadFile = (name = "bento.jpg") => {
  const input = screen.getByLabelText("Choose a pet photo");
  fireEvent.change(input, { target: { files: [new File(["img-bytes"], name, { type: "image/jpeg" })] } });
};

/** Stateful harness — PhotoUpload is a controlled component. */
function Harness({ spy }: { spy: (r: PhotoUploadResult) => void }) {
  const [uploaded, setUploaded] = useState<PhotoUploadResult | null>(null);
  return (
    <PhotoUpload
      uploaded={uploaded}
      onUploaded={(r) => {
        spy(r);
        setUploaded(r);
      }}
    />
  );
}

describe("PhotoUpload (YOLOv8 gatekeeper UX)", () => {
  it("uploads a pet photo and shows the preview + detected badge", async () => {
    const onUploaded = vi.fn();
    renderWithProviders(<Harness spy={onUploaded} />);
    uploadFile("bento.jpg");
    expect(await screen.findByAltText("Uploaded pet preview")).toBeInTheDocument();
    expect(screen.getByText("Pet detected ✓")).toBeInTheDocument();
    await waitFor(() =>
      expect(onUploaded).toHaveBeenCalledWith(expect.objectContaining({ key: "pets/photos/bento.jpg", pet_classes: ["dog"] })),
    );
  });

  it("shows the 422 no-pet error with detected labels and allows retry — no ban", async () => {
    setUploadRejects(true);
    const onUploaded = vi.fn();
    renderWithProviders(<PhotoUpload onUploaded={onUploaded} uploaded={null} />);
    uploadFile("landscape.jpg");
    const alert = await screen.findByTestId("no-pet-error");
    expect(alert).toHaveTextContent("No pet detected in the photo.");
    expect(alert).toHaveTextContent("person, car");
    expect(alert).toHaveTextContent("No strikes, no bans");
    expect(onUploaded).not.toHaveBeenCalled();
    // Retry is possible: the choose button is still available.
    expect(screen.getByRole("button", { name: /Choose a (different )?photo/ })).toBeEnabled();
  });

  it("shows a generic error box for non-422 failures", async () => {
    mswServer.use(http.post("*/api/pets/photos", () => HttpResponse.json({ error: { code: "server_error", message: "Upload storage unavailable." } }, { status: 500 })));
    const onUploaded = vi.fn();
    renderWithProviders(<PhotoUpload onUploaded={onUploaded} uploaded={null} />);
    uploadFile();
    expect(await screen.findByRole("alert")).toHaveTextContent("Upload storage unavailable.");
  });

  it("renders the existing uploaded photo when provided", () => {
    renderWithProviders(
      <PhotoUpload
        onUploaded={() => {}}
        uploaded={{ key: "k", url: "http://x/full.jpg", thumb_key: "t", thumb_url: "http://x/thumb.jpg", pet_classes: ["cat"], detected_classes: ["cat"], max_confidence: 0.9 }}
      />,
    );
    expect(screen.getByAltText("Uploaded pet preview")).toHaveAttribute("src", "http://x/thumb.jpg");
    expect(screen.getByRole("button", { name: /Choose a different photo/ })).toBeInTheDocument();
  });
});
