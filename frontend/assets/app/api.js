export async function get(url) {
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw Error(body.detail || response.statusText);
  }
  return response.json();
}
