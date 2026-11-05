import { addIcon } from "@iconify/vue";

export function registerCustomIconifyIcons() {
  // Teleperformance Icon
  addIcon("brand-teleperformance", {
    body: `<path
        d="M14.2188 4L4.98945 4.0025C4.69869 3.9963 4.43521 4.25921 4.44699 4.55059C4.44513 5.48239 4.44705 6.41349 4.44582 7.34467C4.4421 7.50462 4.48236 7.67206 4.60449 7.78242L7.90141 11.0434L7.90452 7.64603C7.90518 7.55639 7.79296 7.52823 7.72105 7.53443C6.91324 7.53257 6.10545 7.53879 5.29827 7.53259C5.12344 7.54871 4.95541 7.398 4.97463 7.21883C4.97153 6.43272 4.97399 5.64667 4.97337 4.86056C4.94857 4.67582 5.11346 4.50967 5.29759 4.52889L13.721 4.53199C13.889 4.53323 14.0149 4.69814 13.9994 4.86056C14.0019 5.64605 14.005 6.43209 13.9981 7.21758C14.0074 7.36885 13.8928 7.50276 13.7483 7.53376C12.9356 7.53252 12.1234 7.53627 11.3106 7.5332C11.2331 7.5456 11.1147 7.50774 11.0738 7.59887C11.033 10.8143 11.0556 14.2277 11.0577 17.0173C11.0726 17.1357 11.0093 17.2375 10.951 17.3342C10.6826 17.403 10.4036 17.3707 10.1302 17.3763L8.1218 17.3542C8.1218 17.3542 9.44208 18.7594 10.1061 19.4005C10.3819 19.6463 10.6498 19.9596 10.943 20L13.4854 19.9876C13.6925 19.9647 13.8419 19.76 13.8301 19.5573C13.835 17.6968 13.8258 15.8357 13.8344 13.9746C13.8425 13.7787 14.106 13.8636 14.233 13.8419C14.233 13.8419 19.5346 14.0855 19.5544 9.03362C19.5346 4.04576 14.1968 4.00336 14.2188 4Z"
        fill="url(#paint0_linear_2734_85135)" />
    <defs>
        <linearGradient id="paint0_linear_2734_85135" x1="4.25675" y1="12.2458" x2="19.3822"
            y2="12.1464" gradientUnits="userSpaceOnUse">
            <stop stop-color="#742B8E" />
            <stop offset="1" stop-color="#EB1E81" />
        </linearGradient>
    </defs>`,
    width: 24,
    height: 24,
  });

  // Wati Icon
  addIcon("brand-wati", {
    body: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path
        d="M8.61863 16.7031H13.3477L16.1739 19.7294V16.7031H17.3814C18.8219 16.7031 20 15.4404 20 13.8965V9.91064C20 8.36678 18.8219 7.10413 17.3814 7.10413H8.61863C7.17813 7.10413 6 8.36678 6 9.91064V13.8965C6 15.4404 7.17813 16.7031 8.61863 16.7031Z"
        fill="#00E785" />
    <path
        d="M14.6725 18.6773L11.6374 15.4859H7.12415C5.4018 15.4859 4 14.0107 4 12.1981V8.28781C4 6.47523 5.4018 5 7.12415 5H15.8758C17.5982 5 19 6.47523 19 8.28781V12.1968C19 14.0093 17.5982 15.4846 15.8758 15.4846H14.6699V14.4136H15.8758C17.0372 14.4136 17.9824 13.419 17.9824 12.1968V8.28781C17.9824 7.06559 17.0372 6.07095 15.8758 6.07095H7.12415C5.96277 6.07095 5.01764 7.06559 5.01764 8.28781V12.1968C5.01764 13.419 5.96277 14.4136 7.12415 14.4136H12.0584L14.6814 17.1713L14.6725 18.676V18.6773Z"
        fill="#1D1D1B" />
</svg>`,
    width: 24,
    height: 24,
  });

  // Rocket
  addIcon("custom:rocket", {
    body: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<g>
<path d="M3.80013 18.2084C3.91679 18.3251 4.07513 18.3834 4.23346 18.3834C4.40013 18.3834 4.55846 18.3168 4.68346 18.1918L6.07513 16.7668C6.31679 16.5168 6.31679 16.1251 6.06679 15.8834C5.81679 15.6501 5.42513 15.6501 5.18346 15.9001L3.79179 17.3251C3.55013 17.5751 3.55013 17.9668 3.80013 18.2084Z" fill="currentColor"/>
<path fill-rule="evenodd" clip-rule="evenodd" d="M9.67516 18.3752C9.70849 18.3835 9.79182 18.3835 9.79182 18.3835L9.78349 18.3918C9.94182 18.3918 10.0918 18.3335 10.2085 18.2252L12.3252 16.2585C12.9585 15.6668 13.3252 14.8335 13.3252 13.9668V12.9335C17.1585 10.8752 18.7002 7.57513 18.3252 2.30013C18.3085 1.9918 18.0585 1.75013 17.7502 1.72513C12.4752 1.3418 9.17516 2.8918 7.12513 6.7168H6.0918C5.22513 6.7168 4.3918 7.08347 3.80013 7.7168L1.83347 9.8335C1.6918 9.97517 1.63347 10.1752 1.67513 10.3752C1.7168 10.5752 1.8418 10.7418 2.02513 10.8252C2.02513 10.8252 2.03006 10.8275 2.03667 10.8307C2.24397 10.9298 5.12522 12.3086 6.43347 13.6168C7.73554 14.927 9.12399 17.8147 9.21999 18.0145C9.22291 18.0206 9.22516 18.0252 9.22516 18.0252C9.31682 18.2085 9.47516 18.3335 9.67516 18.3752ZM12.9167 8.75008C13.8372 8.75008 14.5833 8.00392 14.5833 7.08345C14.5833 6.16297 13.8372 5.41678 12.9167 5.41678C11.9962 5.41678 11.25 6.16297 11.25 7.08345C11.25 8.00392 11.9962 8.75008 12.9167 8.75008Z" fill="currentColor"/>
<path d="M1.02513 17.2585C1.1418 17.3752 1.30013 17.4335 1.45847 17.4335C1.62513 17.4335 1.78347 17.3669 1.90847 17.2419L4.22513 14.8585C4.4668 14.6085 4.4668 14.2169 4.2168 13.9752C3.9668 13.7419 3.57513 13.7419 3.33347 13.9919L1.0168 16.3752C0.775134 16.6252 0.775134 17.0169 1.02513 17.2585Z" fill="currentColor"/>
</g>
</svg>
`,
    width: 20,
    height: 20,
  });

  // Page check
  addIcon("custom:page-check", {
    body: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<g>
<path d="M6.45837 1.6665C4.73248 1.6665 3.33337 3.06561 3.33337 4.7915V15.2082C3.33337 16.9341 4.73248 18.3332 6.45837 18.3332H10.8085L9.70854 17.2209C8.98037 16.4847 8.98696 15.2975 9.72329 14.5693C10.4595 13.8412 11.6467 13.8478 12.3749 14.5841L12.7009 14.9137L16.6667 10.2791V4.7915C16.6667 3.06561 15.2676 1.6665 13.5417 1.6665H6.45837Z" fill="currentColor"/>
<path d="M17.774 12.689C17.9935 12.4227 17.9555 12.0288 17.6891 11.8092C17.4228 11.5897 17.0289 11.6277 16.8093 11.894L12.7851 16.7767L11.486 15.463C11.2433 15.2176 10.8475 15.2153 10.6021 15.4581C10.3567 15.7008 10.3545 16.0965 10.5972 16.3419L12.383 18.1477C12.5073 18.2733 12.679 18.3405 12.8556 18.3325C13.0322 18.3245 13.1972 18.2421 13.3096 18.1057L17.774 12.689Z" fill="currentColor"/>
</g>
</svg>
`,
    width: 20,
    height: 20,
  });

  // Megaphone
  addIcon("custom:megaphone", {
    body: `
<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M15.2048 11.6667C16.5854 11.6667 17.7048 10.5474 17.7048 9.16667C17.7048 7.78597 16.5854 6.66668 15.2048 6.66668M10.4792 15.2083C10.136 16.1793 9.20993 16.875 8.12142 16.875C6.74071 16.875 5.62142 15.7558 5.62142 14.375V13.125M5.62325 5.20834V13.125M15.2048 5.68002V12.6533C15.2048 14.3363 13.5753 15.5386 11.9673 15.0421L4.05055 12.5978C3.00274 12.2743 2.28809 11.3057 2.28809 10.209V8.12434C2.28809 7.02772 3.00274 6.05912 4.05055 5.7356L11.9673 3.29129C13.5753 2.79477 15.2048 3.99699 15.2048 5.68002Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
`,
    width: 20,
    height: 20,
  });

  // Generic logo
  addIcon("custom:logo", {
    body: `
<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M5.20801 10C5.20801 11.0355 4.36854 11.875 3.33301 11.875C2.29747 11.875 1.45801 11.0355 1.45801 10C1.45801 8.9645 2.29747 8.125 3.33301 8.125C4.36854 8.125 5.20801 8.9645 5.20801 10Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="square"/>
<path d="M18.542 10C18.542 11.0355 17.7025 11.875 16.667 11.875C15.6315 11.875 14.792 11.0355 14.792 10C14.792 8.9645 15.6315 8.125 16.667 8.125C17.7025 8.125 18.542 8.9645 18.542 10Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="square"/>
<path d="M5.41699 10H14.5837" stroke="currentColor" stroke-width="1.5" stroke-linecap="square"/>
<path d="M2.99023 7.91667C3.88935 4.9047 6.68796 2.70834 10.0011 2.70834C13.3142 2.70834 16.1128 4.9047 17.012 7.91667" stroke="currentColor" stroke-width="1.5" stroke-linecap="square"/>
<path d="M17.012 12.0833C16.1128 15.0953 13.3142 17.2917 10.0011 17.2917C6.68797 17.2917 3.88936 15.0953 2.99023 12.0833" stroke="currentColor" stroke-width="1.5" stroke-linecap="square"/>
</svg>

`,
    width: 20,
    height: 20,
  });

  // Color palette
  addIcon("custom:color-palette", {
    body: `
<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M17.7087 10C17.7087 15.9245 11.3813 10.6649 10.0003 13.4313C9.14382 15.1471 12.4218 17.2917 10.0003 17.2917C5.74313 17.2917 2.29199 14.0271 2.29199 10C2.29199 5.97293 5.74313 2.70834 10.0003 2.70834C14.2575 2.70834 17.7087 5.97293 17.7087 10Z" stroke="currentColor" stroke-width="1.5"/>
<path d="M9.58333 6.45833C9.58333 7.03363 9.117 7.5 8.54167 7.5C7.96637 7.5 7.5 7.03363 7.5 6.45833C7.5 5.88303 7.96637 5.41666 8.54167 5.41666C9.117 5.41666 9.58333 5.88303 9.58333 6.45833Z" stroke="currentColor" stroke-width="1.5"/>
<path d="M7.08333 9.99999C7.08333 10.5753 6.61697 11.0417 6.04167 11.0417C5.46637 11.0417 5 10.5753 5 9.99999C5 9.42466 5.46637 8.95833 6.04167 8.95833C6.61697 8.95833 7.08333 9.42466 7.08333 9.99999Z" stroke="currentColor" stroke-width="1.5"/>
<path d="M13.7503 7.70833C13.7503 8.28363 13.284 8.75 12.7087 8.75C12.1333 8.75 11.667 8.28363 11.667 7.70833C11.667 7.13303 12.1333 6.66666 12.7087 6.66666C13.284 6.66666 13.7503 7.13303 13.7503 7.70833Z" stroke="currentColor" stroke-width="1.5"/>
</svg>

`,
    width: 20,
    height: 20,
  });

  // Typography
  addIcon("custom:typography", {
    body: `
<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M3.125 5.20833V3.125H10H16.875V5.20833" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M10 16.875V3.125" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M8.125 16.875H10H11.875" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
`,
    width: 20,
    height: 20,
  });

  // Summary
  addIcon("custom:arrow-split", {
    body: `
<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M3.125 7.70833V3.125M3.125 3.125H7.70833M3.125 3.125L10 10M10 10L16.875 3.125M10 10V16.875M12.2917 3.125H16.875M16.875 3.125V7.70833" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
`,
    width: 20,
    height: 20,
  });

  // Summary
  addIcon("custom:summary", {
    body: `
<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M3.125 4.79166V11.875C3.125 13.2557 4.24429 14.375 5.625 14.375H16.0417" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M15 15.8333V12.9167L16.875 14.375L15 15.8333Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M6.875 6.04166H13.9583" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M6.875 10.2083H11.0417" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
`,
    width: 20,
    height: 20,
  });

  // Trash
  addIcon("custom:trash", {
    body: `
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M4.75 6.5L5.58982 18.4601C5.70016 20.0316 7.00714 21.25 8.58245 21.25H15.4175C16.9929 21.25 18.2998 20.0316 18.4102 18.4601L19.25 6.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M3.25 5.75H20.75" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M8.52539 5.58289C8.73158 3.84652 10.2089 2.5 12.0008 2.5C13.7926 2.5 15.27 3.84652 15.4762 5.58289" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M10 10.5V16.25" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M14 10.5V16.25" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
`,
    width: 24,
    height: 24,
  });

  // North Star
  addIcon("custom:north-star", {
    body: `<path d="M12 1.875L14.25 9.75L22.125 12L14.25 14.25L12 22.125L9.75 14.25L1.875 12L9.75 9.75L12 1.875Z" fill="currentColor"/>`,
    width: 24,
    height: 24,
  });

  // Stack
  addIcon("tabler:stack-0", {
    body: `
<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M9.66667 7L3 10.3333L9.66667 13.6667L16.3333 10.3333L9.66667 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
`,
    width: 20,
    height: 20,
  });

  // Hi Luca v2
  addIcon("custom:hi-luca", {
    body: `<path d="M4.57938 2.12109H0.987628C0.442061 2.12109 0 2.57068 0 3.12526V18.7503H4.57938C5.12495 18.7503 5.56701 18.3007 5.56701 17.7461V3.12526C5.56701 2.57068 5.12495 2.12109 4.57938 2.12109Z" fill="currentColor"/>
<path d="M12.0344 0H7.96635C7.48016 0 7.08594 0.446666 7.08594 0.997916V19.0021C7.08594 19.5533 7.48016 20 7.96635 20H12.9148V0.997916C12.9148 0.446666 12.5206 0 12.0344 0Z" fill="currentColor"/>
<path d="M19.0125 1.25H14.4331V16.3758C14.4331 16.9271 14.8752 17.3738 15.4207 17.3738H19.0125C19.5581 17.3738 20.0001 16.9271 20.0001 16.3758V2.24792C20.0001 1.69667 19.5581 1.25 19.0125 1.25Z" fill="currentColor"/>`,
    width: 20,
    height: 20,
  });

  // Filled pin (pinned format)
  addIcon("custom:pin-filled", {
    body: `<path fill-rule="evenodd" clip-rule="evenodd" d="M7.49992 3.33331V8.33331L5.83325 11.6666V13.3333H14.1666V11.6666L12.4999 8.33331V3.33331" fill="currentColor"/>
<path d="M7.49992 3.33331V8.33331L5.83325 11.6666V13.3333H14.1666V11.6666L12.4999 8.33331V3.33331" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M9.99992 13.3333V17.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M6.66675 3.33335H13.3334" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>`,
    width: 20,
    height: 20,
  });
}
