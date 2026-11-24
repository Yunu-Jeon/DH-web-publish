<?php declare(strict_types=1);

namespace IiifInfo;

use Laminas\EventManager\Event;
use Laminas\EventManager\SharedEventManagerInterface;
use Omeka\Module\AbstractModule;

/**
 * 관리자 화면에 IIIF 정보를 더한다.
 * - 아이템 보기: 오른쪽 정보 칸에 매니페스트 링크, 'IIIF' 탭에 매니페스트 ID·캔버스별 미디어·이미지 서비스
 * - 미디어 보기: 오른쪽 정보 칸에 이미지 서비스와 이 미디어가 든 매니페스트
 * 주소 형식은 IIIF Server 모듈의 것(/iiif/{버전}/{id}/manifest, /iiif/{버전}/{미디어 id})을 따른다.
 */
class Module extends AbstractModule
{
    public function getConfig()
    {
        return include __DIR__ . '/config/module.config.php';
    }

    public function attachListeners(SharedEventManagerInterface $sharedEventManager): void
    {
        $sharedEventManager->attach('Omeka\Controller\Admin\Item', 'view.show.section_nav', [$this, 'addSectionNav']);
        $sharedEventManager->attach('Omeka\Controller\Admin\Item', 'view.show.after', [$this, 'showItemSection']);
        $sharedEventManager->attach('Omeka\Controller\Admin\Item', 'view.show.sidebar', [$this, 'showItemSidebar']);
        $sharedEventManager->attach('Omeka\Controller\Admin\Media', 'view.show.sidebar', [$this, 'showMediaSidebar']);
    }

    public function addSectionNav(Event $event): void
    {
        $sectionNav = $event->getParam('section_nav');
        $sectionNav['iiif-info'] = 'IIIF';
        $event->setParam('section_nav', $sectionNav);
    }

    public function showItemSection(Event $event): void
    {
        $view = $event->getTarget();
        echo $view->partial('iiif-info/item-section', ['item' => $view->item]);
    }

    public function showItemSidebar(Event $event): void
    {
        $view = $event->getTarget();
        echo $view->partial('iiif-info/item-sidebar', ['item' => $view->item]);
    }

    public function showMediaSidebar(Event $event): void
    {
        $view = $event->getTarget();
        echo $view->partial('iiif-info/media-sidebar', ['media' => $view->media]);
    }
}
