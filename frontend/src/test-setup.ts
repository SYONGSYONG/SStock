import "@testing-library/jest-dom";

// jsdom은 scrollIntoView를 구현하지 않으므로 no-op으로 채운다(키보드 검색 테스트용).
if (!HTMLElement.prototype.scrollIntoView) {
  HTMLElement.prototype.scrollIntoView = () => {};
}
