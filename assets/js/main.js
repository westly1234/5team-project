// assets/js/main.js 파일의 내용

document.addEventListener('DOMContentLoaded', () => {
    const section = document.getElementById('featureSection');
    const imageItems = document.querySelectorAll('.image-item');
    const textContents = document.querySelectorAll('.text-content');
    
    const viewDetailsBtn = document.getElementById('viewDetailsBtn');
    const featureSection = document.getElementById('featureSection');

    // '자세히 보기' 버튼이 존재할 경우에만 이벤트를 추가합니다.
    if (viewDetailsBtn && featureSection) {
        viewDetailsBtn.addEventListener('click', () => {
            featureSection.scrollIntoView({ behavior: 'smooth' });
        });
    }

    // 이미지 아이템 클릭 이벤트를 추가합니다.
    imageItems.forEach(item => {
        item.addEventListener('click', () => {
            const featureId = item.dataset.feature;
            const isActive = item.classList.contains('active');

            section.classList.remove('active');
            imageItems.forEach(i => i.classList.remove('active'));
            textContents.forEach(tc => tc.classList.remove('active'));

            if (!isActive) {
                section.classList.add('active');
                item.classList.add('active');
                
                const targetText = document.querySelector(`.text-content[data-feature="${featureId}"]`);
                if (targetText) {
                    targetText.classList.add('active');
                }
            }
        });
    });
});